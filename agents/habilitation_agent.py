"""Habilitation Agent - REFSAM habilitation management service"""

import requests
from typing import Dict


class HabilitationAgent:
    def __init__(self, base_url: str = "http://localhost:8089/mock"):
        self.name = "HabilitationAgent"
        self.description = "REFSAM habilitation management service - handles all CRUD operations for user permissions and habilitations"
        self.base_url = base_url
        self._token = None

    def list_habilitations(self) -> Dict:
        """List all habilitations in the system."""
        try:
            headers = {}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            response = requests.get(f"{self.base_url}/habilitations", headers=headers)
            if response.status_code == 200:
                return response.json()
            return {"error": f"Failed to list habilitations: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def get_habilitation(self, hab_id: str) -> Dict:
        """Get detailed information about a specific habilitation."""
        try:
            headers = {}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            response = requests.get(
                f"{self.base_url}/habilitations/{hab_id}", headers=headers
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"Failed to get habilitation: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def create_habilitation(self, payload: Dict) -> Dict:
        """Create a new habilitation for a collaborator."""
        try:
            headers = {"Content-Type": "application/json"}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            response = requests.post(
                f"{self.base_url}/habilitations", json=payload, headers=headers
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"Failed to create habilitation: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def update_habilitation(self, hab_id: str, payload: Dict) -> Dict:
        """Update an existing habilitation."""
        try:
            headers = {"Content-Type": "application/json"}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            response = requests.put(
                f"{self.base_url}/habilitations/{hab_id}", json=payload, headers=headers
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"Failed to update habilitation: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def delete_habilitation(self, hab_id: str) -> Dict:
        """Delete a habilitation."""
        try:
            headers = {}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            response = requests.delete(
                f"{self.base_url}/habilitations/{hab_id}", headers=headers
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"Failed to delete habilitation: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def get_user_habilitations(self, cuid: str) -> Dict:
        """Get all habilitations for a specific user."""
        try:
            headers = {}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            response = requests.get(
                f"{self.base_url}/habilitations/user/{cuid}", headers=headers
            )
            if response.status_code == 200:
                return response.json()
            return {
                "error": f"Failed to get user habilitations: {response.status_code}"
            }
        except Exception as e:
            return {"error": str(e)}

    def check_eligibility(self, cuid: str) -> Dict:
        """Check if a collaborator is eligible for e-Learning application."""
        try:
            headers = {}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            response = requests.get(
                f"{self.base_url}/eligibility/{cuid}", headers=headers
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"Failed to check eligibility: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
