"""CEO Agent - Email and communication service"""

import requests
from typing import Dict


class CeoAgent:
    def __init__(self, base_url: str = "http://localhost:8089/mock"):
        self.name = "CeoAgent"
        self.description = "Email communication service"
        self.base_url = base_url
        self._token = None

    def token(self, client_id: str, secret: str) -> Dict:
        """Get authentication token for CEO service."""
        try:
            payload = {
                "client_id": client_id,
                "client_secret": secret,
                "grant_type": "client_credentials",
            }
            response = requests.post(
                f"{self.base_url}/auth/token",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 200:
                result = response.json()
                self._token = result.get("access_token")
                return result
            return {"error": f"Failed to get token: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def get_template(self, id: str) -> Dict:
        """Get email template by ID."""
        try:
            headers = {}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            response = requests.get(
                f"{self.base_url}/mailTemplate/{id}", headers=headers
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"Failed to get template: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def send_mail(self, payload: Dict) -> Dict:
        """Send email using CEO service."""
        try:
            headers = {"Content-Type": "application/json"}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            response = requests.post(
                f"{self.base_url}/sendMail", json=payload, headers=headers
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"Failed to send email: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
