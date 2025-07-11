# TODO: For production, you should use a more secure way to store session data.
# For example, use a database or a secure cache like Redis.
# Here we use a simple in-memory dictionary for demonstration purposes.
# This will not persist across server restarts and is not thread-safe.
# In a production environment, consider using a more robust session management solution.
SESSION_CARTS = {}


def get_cart_for_session(session_id: str) -> list[dict]:
    """Retrieve cart for a specific session."""
    return SESSION_CARTS.get(session_id, [])


def add_product_to_cart(session_id: str, product: dict):
    """Add a product to the cart for the given session_id.
    If the product already exists, increment its quantity."""
    if session_id not in SESSION_CARTS:
        SESSION_CARTS[session_id] = []

    cart = SESSION_CARTS[session_id]

    # For weighted products, don't combine - each weight is unique
    if "gramm" in product:
        # Always add as new item for weighted products
        new_item = {
            "id": product["id"],
            "name": product["name"],
            "price": float(product["price"]),
            "quantity": 1,  # Always 1 for weighted products
            "img": product.get("img"),
            "category_id": product.get("category_id"),
            "category_name": product.get("category_name"),
            "gramm": product["gramm"],
        }
        cart.append(new_item)
        return

    # For regular products, combine quantities
    for item in cart:
        if item["id"] == product["id"] and "gramm" not in item:
            item["quantity"] += product.get("quantity", 1)
            return

    # Add new regular product
    new_item = {
        "id": product["id"],
        "name": product["name"],
        "price": float(product["price"]),
        "quantity": product.get("quantity", 1),
        "img": product.get("img"),
        "category_id": product.get("category_id"),
        "category_name": product.get("category_name"),
    }
    cart.append(new_item)


def update_cart_quantity(session_id: str, product_id: str, quantity: int):
    """Update the quantity of a product in the cart."""
    cart = SESSION_CARTS.get(session_id, [])
    for item in cart:
        if item["id"] == product_id:
            item["quantity"] = quantity
            break


def remove_cart_item(session_id: str, product_id: str):
    """Remove a product from the cart."""
    cart = SESSION_CARTS.get(session_id, [])
    SESSION_CARTS[session_id] = [
        item for item in cart if str(item["id"]) != str(product_id)
    ]


def clear_cart(session_id: str):
    """Clear the cart for a specific session."""
    if session_id in SESSION_CARTS:
        SESSION_CARTS[session_id] = []
