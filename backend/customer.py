import httpx
import re

INSTANCE_URL = "https://openfoodnetwork.de"


# Fetch customers from Open Food Network API
def fetch_customers(ofn_api_key: str) -> list[dict]:
    """Fetch customers list from Open Food Network API using httpx."""
    headers = {
        "Accept": "application/json;charset=UTF-8",
        "Content-Type": "application/json",
    }
    url = f"{INSTANCE_URL}/api/v1/customers?token={ofn_api_key}"
    try:
        with httpx.Client() as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            raw = response.json()
            customers = []
            for item in raw.get("data", []):
                attrs = item.get("attributes", {})
                # Merge id and enterprise_id from relationships if needed
                attrs["id"] = attrs.get("id", item.get("id"))
                attrs["enterprise_id"] = attrs.get("enterprise_id", None)
                customers.append(attrs)
            return customers
    except httpx.RequestError as e:
        print(f"Failed to fetch customers: {e}")
        return []


def find_customer_by_code(code: str, customers: list[dict]) -> dict:
    """Find a customer by code in their tags."""
    pattern = re.compile(rf"code[:=]{re.escape(code)}(\b|;|$)", re.IGNORECASE)
    for customer in customers:
        code_found = False
        iban = ""
        # Search for code and IBAN in tags
        for tag in customer.get("tags", []):
            if pattern.search(tag):
                code_found = True
            if tag.lower().startswith("iban:"):
                iban = tag.split(":", 1)[1].strip()
        if code_found:
            name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
            return {
                "exist": True,
                "id": customer.get("id"),
                "code": code,
                "full_name": name,
                "first_name": customer.get("first_name", ""),
                "last_name": customer.get("last_name", ""),
                "email": customer.get("email", ""),
                "iban": iban,
                "bill_address": customer.get("billing_address", {}),
                "ship_address": customer.get("shipping_address", {}),
            }
    return {"exist": False}
