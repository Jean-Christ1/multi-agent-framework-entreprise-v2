"""Geai Agent - Identity and organizational management"""

import requests
from typing import Dict, List


class GeaiAgent:
    def __init__(self, base_url: str = "http://localhost:8089/mock"):
        self.name = "GeaiAgent"
        self.description = "Identity management and organizational services"
        self.base_url = base_url

    def get_status(self, cuid: str) -> Dict:
        """Get status for a specific user."""
        try:
            response = requests.get(f"{self.base_url}/status/{cuid}")
            if response.status_code == 200:
                return response.json()
            return {"error": f"Failed to get status: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def email_rename(self, cuid: str, new_mail: str) -> Dict:
        """Request email address change for a user."""
        try:
            payload = {"cuid": cuid, "newEmail": new_mail}
            response = requests.post(
                f"{self.base_url}/emailRename",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"Failed to rename email: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def replace_manager(self, emp_cuid: str, mgr_cuid: str) -> Dict:
        """Replace manager for an employee."""
        try:
            payload = {"employeeCuid": emp_cuid, "newManagerCuid": mgr_cuid}
            response = requests.post(
                f"{self.base_url}/replaceManager",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"Failed to replace manager: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def create_identity(self, person_data: Dict) -> Dict:
        """Create a new identity in the system."""
        try:
            # Validate required fields
            required_fields = ["cuid", "firstName", "lastName", "email"]
            for field in required_fields:
                if field not in person_data:
                    return {"error": f"Missing required field: {field}"}

            response = requests.post(
                f"{self.base_url}/createIdentity",
                json=person_data,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "message": f"Identity created successfully for {person_data['firstName']} {person_data['lastName']}",
                    "cuid": person_data["cuid"],
                    "identity": result,
                    "source": "GeaiAgent",
                    "operation": "create_identity",
                }
            return {"error": f"Failed to create identity: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def list_identities(self, cuid: str) -> List[Dict]:
        """List all identities for a user."""
        try:
            response = requests.get(f"{self.base_url}/Identities/{cuid}")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            return [{"error": str(e)}]

    def get_er_group(self, cuid: str) -> Dict:
        """Get ER group information for a user."""
        try:
            response = requests.get(f"{self.base_url}/ergroup/{cuid}")
            if response.status_code == 200:
                return response.json()
            return {"error": f"Failed to get ER group: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def get_eburo(self, cuid: str) -> Dict:
        """Get eBuro information for a user."""
        try:
            response = requests.get(f"{self.base_url}/eburo/{cuid}")
            if response.status_code == 200:
                return response.json()
            return {"error": f"Failed to get eBuro: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
