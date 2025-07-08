import asyncio
import serial
import websockets
import json
import uuid
import re
import time

from smartcard.System import readers

from api import get_nanostore_settings, IQToolAPI
from card import get_card_uid_async
from cart import (
    get_cart_for_session,
    add_product_to_cart,
    update_cart_quantity,
    remove_cart_item,
    clear_cart,
)
from customer import fetch_customers, find_customer_by_code
from product import load_products
from scale import get_scale_port
from relay import trigger_relay
from order import create_ofn_order_from_session


BAUDRATE = 9600
WEBSOCKET_PORT = 8765

# TODO: For production, you should use a more secure way to store session data.
# For example, use a database or a secure cache like Redis.
# Here we use a simple in-memory dictionary for demonstration purposes.
# This will not persist across server restarts and is not thread-safe.
# In a production environment, consider using a more robust session management solution.
SESSION_CUSTOMERS = {}
SESSION_LAST_ACTIVITY = {}

OFN_API_KEY = get_nanostore_settings(key="OFN_API_KEY")
OFN_ADMIN_EMAIL = get_nanostore_settings(key="OFN_ADMIN_EMAIL")
OFN_ADMIN_PASSWORD = get_nanostore_settings(key="OFN_ADMIN_PASSWORD")
OFN_SHOP_ID = get_nanostore_settings(key="OFN_SHOP_ID")
ORDER_CYCLE_ID = get_nanostore_settings(key="ORDER_CYCLE_ID")
OFN_PAYMENT_METHOD_ID = get_nanostore_settings(key="OFN_PAYMENT_METHOD_ID")
TIMEOUT_SHOPPING_CART = int(get_nanostore_settings(key="TIMEOUT_SHOPPING_CART"))

api_service = IQToolAPI()


def update_last_activity(session_id):
    SESSION_LAST_ACTIVITY[session_id] = time.time()


async def handle_websocket(websocket):
    print("WebSocket connection opened")
    try:
        async for command in websocket:
            print(f"Received: {command}")

            # --- JSON-based protocol for Vue frontend ---
            try:
                msg = json.loads(command)
            except Exception:
                await asyncio.sleep(0.01)
                continue

            # --- Session ID logic ---
            session_id = msg.get("session_id")
            if not session_id:
                # Generate a new session_id and send it to the client
                session_id = str(uuid.uuid4())
                await websocket.send(
                    json.dumps({"type": "session_id", "session_id": session_id})
                )

            # Open door (card scan listener) Entrance
            if msg.get("type") == "open_door":
                timeout = 8000
                trigger_relay(timeout)
                await websocket.send(json.dumps({"type": "open_door", "status": "OK"}))

                code = msg.get("code")
                is_entrance = True
                customer_firstname = ""
                customer_lastname = ""

                try:
                    customers = fetch_customers(OFN_API_KEY)
                    customer_data = find_customer_by_code(code, customers)
                    customer_firstname = customer_data.get("first_name", "")
                    customer_lastname = customer_data.get("last_name", "")
                except Exception as e:
                    print(f"Error fetching customer data: {e}")
                    is_entrance = False

                # If customer_firstname/lastname are empty, treat as not granted
                if not customer_firstname and not customer_lastname:
                    is_entrance = False

                payload = {
                    "customer_firstname": customer_firstname,
                    "customer_lastname": customer_lastname,
                    "rfid_card_id": code,
                    "is_entrance": is_entrance,
                    "ofn_hub_id": OFN_SHOP_ID,
                }
                try:
                    api_service.post("entrance-history/create/", payload)
                    print(
                        f"Entrance history logged to IQ Tool (is_entrance={is_entrance})."
                    )
                except Exception as e:
                    print(f"Failed to log entrance history: {e}")

            # Login (card scan listener) POS
            elif msg and msg.get("type") == "login":
                all_readers = readers()
                if len(all_readers) > 1:
                    device = str(all_readers[1])
                else:
                    device = str(all_readers[0])
                card_uid = await get_card_uid_async(device)
                await websocket.send(
                    json.dumps({"type": "customer_code", "code": card_uid})
                )

            # Check code, log in the shopping cart
            elif msg.get("type") == "check_customer_code":
                code = msg.get("code")
                customers = fetch_customers(OFN_API_KEY)
                customer_data = find_customer_by_code(code, customers)
                # Save customer data for this session
                SESSION_CUSTOMERS[session_id] = customer_data
                await websocket.send(
                    json.dumps({"type": "customer_code_checked", **customer_data})
                )

            # Cart logic
            elif msg.get("type") == "get_cart":
                cart = get_cart_for_session(session_id)
                await websocket.send(json.dumps({"type": "cart", "cart": cart}))

            # Products load
            elif msg.get("type") == "load_products":
                products_data = load_products(OFN_API_KEY, OFN_SHOP_ID)
                await websocket.send(
                    json.dumps({"type": "load_products", **products_data})
                )

            elif msg.get("type") == "check_product_code":
                code = (
                    str(msg.get("code", ""))
                    .replace("Shift", "")
                    .replace("Meta", "")
                    .lower()
                )
                products_data = load_products(OFN_API_KEY, OFN_SHOP_ID)
                product_array = products_data.get("product_array", {})
                found = None
                for key, p in product_array.items():
                    item_code = str(p.get("sku", "")).lower()
                    if item_code == code:
                        found = {
                            "exist": True,
                            "id": key,
                            "name": p.get("name"),
                            "price": p.get("price"),
                            "img": p.get("image"),
                            "category_id": p.get("category_id"),
                            "category_name": p.get("category_name"),
                        }
                        break
                if found:
                    await websocket.send(
                        json.dumps({"type": "search_product_code", **found})
                    )
                else:
                    # If not found by code, try by name (fallback)
                    # You can optionally log this fallback
                    name = code  # treat the code as a possible name
                    product_weight_array = products_data.get("product_weight_array", {})
                    found_name = None
                    for p in product_weight_array.values():
                        if p.get("name", "").lower() == name.lower():
                            found_name = p
                            break
                    if found_name:
                        response = {
                            "type": "search_product_name",
                            "exist": True,
                            "product": {
                                "id": found_name.get("id"),
                                "name": found_name.get("name"),
                                "price": found_name.get("price"),
                                "image": found_name.get("image"),
                                "category_id": found_name.get("category_id"),
                                "category_name": found_name.get("category_name"),
                            },
                            "name": name,
                        }
                    else:
                        response = {
                            "type": "search_product_name",
                            "exist": False,
                            "name": name,
                        }
                    await websocket.send(json.dumps(response))

            elif msg.get("type") == "add_to_cart":
                update_last_activity(session_id)
                add_product_to_cart(
                    session_id,
                    {
                        "id": msg["id"],
                        "name": msg["name"],
                        "price": msg["price"],
                        "img": msg.get("img"),
                        "category_id": msg.get("category_id"),
                        "category_name": msg.get("category_name"),
                    },
                )
                cart = get_cart_for_session(session_id)
                await websocket.send(json.dumps({"type": "cart", "cart": cart}))

            elif msg.get("type") == "update_quantity":
                update_last_activity(session_id)
                update_cart_quantity(session_id, msg["id"], msg["quantity"])
                cart = get_cart_for_session(session_id)
                await websocket.send(json.dumps({"type": "cart", "cart": cart}))

            elif msg.get("type") == "remove_item":
                update_last_activity(session_id)
                remove_cart_item(session_id, msg["id"])
                cart = get_cart_for_session(session_id)
                await websocket.send(json.dumps({"type": "cart", "cart": cart}))

            elif msg.get("type") == "delete_cart":
                clear_cart(session_id)
                await websocket.send(json.dumps({"type": "cart_deleted"}))

            # Weight (for weighted products)
            elif msg.get("type") == "weight":
                port = get_scale_port()
                if not port:
                    await websocket.send(
                        json.dumps({"type": "weight", "error": "Scale not found"})
                    )
                    continue
                try:
                    with serial.Serial(port, BAUDRATE, timeout=1) as ser:
                        line = ser.readline().decode(errors="ignore")
                        if line:
                            match = re.search(r"([-+]?\d*\.\d+|\d+)", line)
                            if match:
                                weight = match.group(0)
                                await websocket.send(
                                    json.dumps({"type": "weight", "value": weight})
                                )
                except Exception as e:
                    await websocket.send(
                        json.dumps({"type": "weight", "error": str(e)})
                    )

            # Checkout logic
            elif msg.get("type") == "checkout":
                customer_data = SESSION_CUSTOMERS.get(session_id, {})

                # Create order from session
                order = create_ofn_order_from_session(
                    session_id,
                    OFN_API_KEY,
                    OFN_ADMIN_EMAIL,
                    OFN_ADMIN_PASSWORD,
                    OFN_SHOP_ID,
                    ORDER_CYCLE_ID,
                    OFN_PAYMENT_METHOD_ID,
                    customer_data,
                )

                await websocket.send(
                    json.dumps({"type": "init_checkout", "order": order})
                )

            # Get confirmation msg from db
            elif msg.get("type") == "get_confirmation":
                confirmation = msg.get("confirmation")
                # TODO: Get the value from the database
                # value = get_setting_from_db(confirmation, "")
                value = "Your confirmation message here"
                await websocket.send(
                    json.dumps(
                        {
                            "type": "confirmation",
                            "confirmation": confirmation,
                            "value": value,
                        }
                    )
                )

    except Exception as e:
        print(f"Error in handle_websocket: {e}")


async def cart_timeout_watcher():
    while True:
        now = time.time()
        to_remove = []
        for session_id, last_activity in SESSION_LAST_ACTIVITY.items():
            if now - last_activity > TIMEOUT_SHOPPING_CART:
                customer_data = SESSION_CUSTOMERS.get(session_id, {})
                # Create order but do not bill
                order = create_ofn_order_from_session(
                    session_id,
                    OFN_API_KEY,
                    OFN_ADMIN_EMAIL,
                    OFN_ADMIN_PASSWORD,
                    OFN_SHOP_ID,
                    ORDER_CYCLE_ID,
                    OFN_PAYMENT_METHOD_ID,
                    customer_data,
                )
                print(f"Session {session_id} timed out. Order created: {order}")
                to_remove.append(session_id)
        # Clean up timed-out sessions
        for session_id in to_remove:
            SESSION_LAST_ACTIVITY.pop(session_id, None)
            SESSION_CUSTOMERS.pop(session_id, None)
        await asyncio.sleep(10)  # Check every 10 seconds


async def main():
    print(f"Starting WebSocket server on ws://localhost:{WEBSOCKET_PORT}")
    server = websockets.serve(handle_websocket, "localhost", WEBSOCKET_PORT)
    await asyncio.gather(
        server,
        cart_timeout_watcher(),
    )
    print("WebSocket server stopped.")


if __name__ == "__main__":
    asyncio.run(main())
