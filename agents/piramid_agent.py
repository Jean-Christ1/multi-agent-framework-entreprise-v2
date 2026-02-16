"""Piramid Agent - Building and identity information service"""

import requests
from typing import Dict, List


class PiramidAgent:
    def __init__(self, base_url: str = "http://localhost:8089/mock"):
        self.name = "PiramidAgent"
        self.description = "Building, company, and identity information service"
        self.base_url = base_url

    def get_building(self, id: str) -> Dict:
        """Get building information by ID."""
        try:
            response = requests.get(f"{self.base_url}/batiment/{id}")
            if response.status_code == 200:
                return response.json()
            return {"error": f"Building not found: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def get_company(self, id: str) -> Dict:
        """Get company information by ID."""
        try:
            response = requests.get(f"{self.base_url}/societe/{id}")
            if response.status_code == 200:
                return response.json()
            return {"error": f"Company not found: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def search_identity(self, query: str) -> List[Dict]:
        """Search for identities by query."""
        try:
            params = {"q": query}
            response = requests.get(f"{self.base_url}/rechercheIdentite", params=params)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            return [{"error": str(e)}]

    def list_identities(self) -> List[Dict]:
        """List all identities."""
        try:
            response = requests.get(f"{self.base_url}/listeidentites")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            return [{"error": str(e)}]

    def get_identity(self, id: str) -> Dict:
        """Get identity information by ID."""
        try:
            response = requests.get(f"{self.base_url}/identites/{id}")
            if response.status_code == 200:
                return response.json()
            return {"error": f"Identity not found: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def get_visit_addresses(self, id: str) -> List[Dict]:
        """Get visit addresses for an identity."""
        try:
            response = requests.get(f"{self.base_url}/adressesvisite/{id}")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            return [{"error": str(e)}]

    def get_managed_identities(self, cuid: str) -> List[Dict]:
        """Get identities managed by a specific user."""
        try:
            response = requests.get(f"{self.base_url}/identitesmanagees/{cuid}")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            return [{"error": str(e)}]
