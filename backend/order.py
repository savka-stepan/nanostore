import httpx
from bs4 import BeautifulSoup
import re
import os

from dotenv import load_dotenv

from cart import get_cart_for_session


load_dotenv()

OFN_ADMIN_EMAIL = os.environ.get("OFN_ADMIN_EMAIL")
OFN_ADMIN_PASSWORD = os.environ.get("OFN_ADMIN_PASSWORD")
OFN_ADMIN_API_KEY = os.environ.get("OFN_ADMIN_API_KEY")

INSTANCE_URL = "https://openfoodnetwork.de"
PRE_LOGIN_URL = f"{INSTANCE_URL}/#/login"
LOGIN_URL = f"{INSTANCE_URL}/user/spree_user/sign_in"
API_ORDER_URL = f"{INSTANCE_URL}/api/v0/orders"
ORDER_URL = f"{INSTANCE_URL}/admin/orders/"
NEW_ORDER_URL = f"{ORDER_URL}/new"


def fetch_authenticity_token(http_client: httpx.Client) -> str:
    """Fetch the CSRF token from the given page URL."""
    resp = http_client.get(PRE_LOGIN_URL)
    soup = BeautifulSoup(resp.text, "html.parser")
    token = soup.find("meta", {"name": "csrf-token"})
    if token:
        return token["content"]
    else:
        token = soup.find("input", {"name": "authenticity_token"})["value"]
        if token:
            return token
        else:
            raise Exception("CSRF token not found on the page.")


def get_session_tokens(http_client: httpx.Client) -> dict:
    """Login and return session cookies (_ofn_session_id, XSRF-TOKEN)."""
    # 1. GET the new order page to get the CSRF token
    authenticity_token = fetch_authenticity_token(http_client)

    # 2. POST login credentials
    payload = {
        "authenticity_token": authenticity_token,
        "spree_user[email]": OFN_ADMIN_EMAIL,
        "spree_user[password]": OFN_ADMIN_PASSWORD,
    }
    http_client.post(LOGIN_URL, data=payload, headers={"Referer": LOGIN_URL})

    # 3. Extract cookies
    cookies = http_client.cookies
    ofn_session_id = cookies.get("_ofn_session_id")
    xsrf_token = cookies.get("XSRF-TOKEN")

    if not ofn_session_id or not xsrf_token:
        raise Exception("Failed to log in and retrieve session cookies.")

    return {
        "_ofn_session_id": ofn_session_id,
        "XSRF-TOKEN": xsrf_token,
    }


def create_order(
    http_client: httpx.Client, distributor_id: str, order_cycle_id: str
) -> str:
    """Create an order and return the order number if successful."""
    # 1. GET the new order page to get the CSRF token
    authenticity_token = fetch_authenticity_token(http_client)

    # 1. Prepare your payload (add all required fields!)
    payload = {
        "authenticity_token": authenticity_token,
        "order[distributor_id]": distributor_id,
        "order[order_cycle_id]": order_cycle_id,
    }

    # 2. POST to create the order
    response = http_client.post(
        ORDER_URL, data=payload, headers={"Referer": NEW_ORDER_URL}
    )
    match = re.search(r"Order\s*#\s*([A-Z0-9]+)", response.text)
    if match:
        order_id = match.group(1)
        return order_id
    else:
        raise Exception("Order number not found in response.")


def get_order_data(order_id: str):
    """Fetch order details via OFN API."""
    url = f"{API_ORDER_URL}/{order_id}?token={OFN_ADMIN_API_KEY}"
    headers = {
        "Accept": "application/json",
    }
    response = httpx.get(url, headers=headers)
    print("Status code:", response.status_code)
    print("Response JSON:", response.json())


def update_customer(
    session_tokens: dict,
    order_id: str,
    customer_data: dict,
):
    """Update customer information for the given order."""
    with httpx.Client(follow_redirects=True, cookies=session_tokens) as http_client:
        # 1. GET the new order page to get the CSRF token
        authenticity_token = fetch_authenticity_token(http_client)

        # 2. Prepare the URL for updating customer information
        url = f"{INSTANCE_URL}/admin/orders/{order_id}/customer"

        # 3. Prepare your payload (add all required fields!)
        bill_address = customer_data.get("bill_address", {})
        ship_address = customer_data.get("ship_address") or bill_address

        # --- You must map codes to OFN IDs here ---
        # For production, fetch these from OFN API or config!
        COUNTRY_CODE_TO_ID = {"DE": "155"}  # Example: Germany
        STATE_CODE_TO_ID = {
            "BW": "54",  # Baden-Württemberg
            "BY": "55",  # Bayern
            "BE": "53",  # Berlin
            "BB": "52",  # Brandenburg
            "HB": "56",  # Bremen
            "HH": "58",  # Hamburg
            "HE": "57",  # Hessen
            "MV": "59",  # Mecklenburg-Vorpommern
            "NI": "60",  # Niedersachsen
            "NW": "61",  # Nordrhein-Westfalen
            "RP": "62",  # Rheinland-Pfalz
            "SL": "64",  # Saarland
            "SN": "65",  # Sachsen
            "ST": "66",  # Sachsen-Anhalt
            "SH": "63",  # Schleswig-Holstein
            "TH": "67",  # Thüringen
        }

        def get_country_id(country):
            if country and "code" in country:
                return COUNTRY_CODE_TO_ID.get(country["code"], "")
            return ""

        def get_state_id(region):
            if region and "code" in region:
                return STATE_CODE_TO_ID.get(region["code"], "")
            return ""

        payload = {
            "_method": "patch",
            "authenticity_token": authenticity_token,
            "order[email]": customer_data.get("email", ""),
            "order[bill_address_attributes][firstname]": bill_address.get(
                "first_name", ""
            ),
            "order[bill_address_attributes][lastname]": bill_address.get(
                "last_name", ""
            ),
            "order[bill_address_attributes][address1]": bill_address.get(
                "street_address_1", ""
            ),
            "order[bill_address_attributes][address2]": bill_address.get(
                "street_address_2"
            )
            or "",
            "order[bill_address_attributes][city]": bill_address.get("locality", ""),
            "order[bill_address_attributes][zipcode]": bill_address.get(
                "postal_code", ""
            ),
            "order[bill_address_attributes][country_id]": get_country_id(
                bill_address.get("country")
            ),
            "order[bill_address_attributes][state_id]": get_state_id(
                bill_address.get("region")
            ),
            "order[bill_address_attributes][phone]": bill_address.get("phone", ""),
            "order[use_billing]": "1",
            "order[ship_address_attributes][firstname]": ship_address.get(
                "first_name", ""
            ),
            "order[ship_address_attributes][lastname]": ship_address.get(
                "last_name", ""
            ),
            "order[ship_address_attributes][address1]": ship_address.get(
                "street_address_1", ""
            ),
            "order[ship_address_attributes][address2]": ship_address.get(
                "street_address_2"
            )
            or "",
            "order[ship_address_attributes][city]": ship_address.get("locality", ""),
            "order[ship_address_attributes][zipcode]": ship_address.get(
                "postal_code", ""
            ),
            "order[ship_address_attributes][country_id]": get_country_id(
                ship_address.get("country")
            ),
            "order[ship_address_attributes][state_id]": get_state_id(
                ship_address.get("region")
            ),
            "order[ship_address_attributes][phone]": ship_address.get("phone", ""),
            "order[customer_id]": customer_data.get("id", ""),
            "button": "",
        }

        # 4. POST to update customer information
        resp = http_client.put(url, data=payload)


def add_line_items(http_client: httpx.Client, order_id: str, cart: list):
    """Add line items to the order."""
    url = f"{INSTANCE_URL}/api/v0/orders/{order_id}/shipments.json?token={OFN_ADMIN_API_KEY}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    for item in cart:
        payload = {
            "variant_id": item["id"],
            "quantity": item["quantity"],
        }
        http_client.post(url, headers=headers, json=payload)


def mark_payment(
    session_tokens: dict, order_id: str, payment_method_id: str, amount: str
):
    """Create a payment for the order."""
    url = f"{INSTANCE_URL}/admin/orders/{order_id}/payments.json"
    headers = {
        "Referer": f"{INSTANCE_URL}/admin/orders/{order_id}/payments/new",
        "x-xsrf-token": session_tokens["XSRF-TOKEN"],
        "User-Agent": "Mozilla/5.0",
    }
    payload = {
        "payment[payment_method_id]": payment_method_id,
        "payment[amount]": amount,
        "order_id": order_id,
    }
    with httpx.Client(follow_redirects=True, cookies=session_tokens) as http_client:
        resp = http_client.post(url, headers=headers, data=payload)


def generate_invoice(order_id: str):
    """Generate an invoice for the order from IQ tool."""
    payload = {"order_no": order_id}
    httpx.post(
        "https://ofn.hof-homann.de/api/generate-invoice-pdf-webhook/",
        json=payload,
        headers={
            "Authorization": "JWT {IQTOOL_JWT_TOKEN}",
            "Content-Type": "application/json",
        },
    )


def create_ofn_order_from_session(
    session_id: str,
    customer_data: dict,
    distributor_id: str,
    order_cycle_id: str,
    payment_method_id: str,
) -> dict:
    # 1. Get the cart for this session
    cart = get_cart_for_session(session_id)
    if not cart:
        raise Exception("Cart is empty.")

    with httpx.Client(follow_redirects=True) as http_client:
        # 2. Get session tokens (login)
        session_tokens = get_session_tokens(http_client)

        # 3. Create the order
        order_id = create_order(http_client, distributor_id, order_cycle_id)

        # 4. Update customer info
        update_customer(session_tokens, order_id, customer_data)

        # 5. Add line items
        add_line_items(http_client, order_id, cart)

        # 6. Create payment
        total = sum(item["price"] * item.get("quantity", 1) for item in cart)
        mark_payment(session_tokens, order_id, payment_method_id, str(total))

    # Return order id, cart
    return {
        "customer": customer_data,
        "order_id": order_id,
        "cart": cart,
        "total": total,
    }
