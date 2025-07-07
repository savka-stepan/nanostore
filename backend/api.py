import os
import httpx

OFN_API_BASE_URL = "https://ofn.hof-homann.de/api/"
IQT_API_EMAIL = os.environ.get("IQT_API_EMAIL")
IQT_API_PASSWORD = os.environ.get("IQT_API_PASSWORD")


class IQToolAPI:
    def __init__(self):
        self.base_url = OFN_API_BASE_URL
        self.email = IQT_API_EMAIL
        self.password = IQT_API_PASSWORD
        self.jwt_token = self.auth(self.email, self.password)
        self.headers = {
            "Authorization": f"JWT {self.jwt_token}",
            "Content-Type": "application/json",
        }

    def auth(self, email, password):
        """Authenticate with IQ Tool API and get JWT token."""
        url = self.base_url + "token-obtain/"
        payload = {"email": email, "password": password}
        response = httpx.post(
            url, json=payload, headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        # Adjust the key if your API returns 'access' instead of 'token'
        return response.json().get("token") or response.json().get("access")

    def post(self, endpoint, payload):
        url = self.base_url + endpoint.lstrip("/")
        response = httpx.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get(self, endpoint, params=None):
        url = self.base_url + endpoint.lstrip("/")
        response = httpx.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()


def get_nanostore_settings(key: str) -> str:
    """Get the Nanostore Settings from IQTool API."""
    api_service = IQToolAPI()
    response = api_service.get(f"nanostore-settings/?key={key}")
    if response and "value" in response:
        return response["value"]
    else:
        raise Exception("OFN API key not found in IQTool settings.")
