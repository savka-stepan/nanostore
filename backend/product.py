import os
import httpx

from dotenv import load_dotenv

load_dotenv()


OFN_ADMIN_API_KEY = os.environ.get("OFN_ADMIN_API_KEY")
INSTANCE_URL = "https://openfoodnetwork.de"


def load_products() -> dict:
    """Load products from Open Food Network API."""
    headers = {
        "Accept": "application/json;charset=UTF-8",
        "Content-Type": "application/json",
        "X-Spree-Token": OFN_ADMIN_API_KEY,
    }
    # TODO: Replace with actual distributor ID
    distributor_id = "256"  # Example distributor ID, adjust as needed
    products_url = f"{INSTANCE_URL}/api/v0/products/bulk_products?q[supplier_id_in]={distributor_id}"
    tax_url = f"{INSTANCE_URL}/api/v0/taxons"
    try:
        with httpx.Client() as client:
            # Fetch products
            products_resp = client.get(products_url, headers=headers)
            products_resp.raise_for_status()
            products_obj = products_resp.json()

            # Fetch taxons (categories)
            tax_resp = client.get(tax_url, headers=headers)
            tax_resp.raise_for_status()
            tax_obj = tax_resp.json()

        # Build category (taxon) lookup: id -> name
        category_lookup = {t["id"]: t["name"] for t in tax_obj}

        product_array = {}
        product_weight_array = {}
        for product in products_obj.get("products", []):
            for variant in product.get("variants", []):
                category_id = variant.get("category_id")
                p = {
                    "id": variant["id"],
                    "sku": variant.get("sku"),
                    "name": variant.get("name_to_display"),
                    "image": (
                        variant.get("image")
                        if "openfoodnetwork.de" in variant.get("image", "")
                        else f"https://openfoodnetwork.de{variant.get('image', '')}"
                    ),
                    "price": variant.get("price"),
                    "category_id": category_id,
                    "category_name": category_lookup.get(category_id, ""),
                }
                if variant.get("variant_unit") == "weight":
                    product_weight_array[variant["id"]] = p
                else:
                    p["sku"] = variant.get("sku")
                    product_array[variant["id"]] = p

        # Build taxonomies/categories array for used categories
        ava = {}
        for o in list(product_weight_array.values()) + list(product_array.values()):
            category_id = o["category_id"]
            if (
                category_id
                and category_id not in ava
                and category_id in category_lookup
            ):
                ava[category_id] = {
                    "id": category_id,
                    "name": category_lookup[category_id],
                }

        return {
            "product_array": product_array,
            "product_weight_array": product_weight_array,
            "taxes_array": ava,
        }
    except Exception as e:
        print(f"Error loading products: {e}")
        return {
            "product_array": {},
            "product_weight_array": {},
            "taxes_array": {},
        }
