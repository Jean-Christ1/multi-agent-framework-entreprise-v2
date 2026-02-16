"""Annuaire Agent - Corporate directory service via SOAP"""

import requests
import xml.etree.ElementTree as ET
from typing import Dict, Optional


class AnnuaireAgent:
    def __init__(self, base_url: str = "http://localhost:8089/mock"):
        self.name = "AnnuaireAgent"
        self.description = "Corporate directory service"
        self.base_url = base_url

    def get_persons(self, criteria_xml: str) -> str:
        """Get persons matching criteria via SOAP."""
        soap_body = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
            <soapenv:Body>
                <getPersonsWithCriterias>
                    {criteria_xml}
                </getPersonsWithCriterias>
            </soapenv:Body>
        </soapenv:Envelope>
        """

        try:
            response = requests.post(
                f"{self.base_url}/PersonService",
                data=soap_body,
                headers={"Content-Type": "text/xml"},
            )
            return response.text
        except Exception as e:
            return f"<error>{str(e)}</error>"

    def get_managed_team(self, manager_cuid: str) -> str:
        """Get the team managed by a person via SOAP."""
        soap_body = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
            <soapenv:Body>
                <getManagedTeam>
                    <uid>{manager_cuid}</uid>
                </getManagedTeam>
            </soapenv:Body>
        </soapenv:Envelope>
        """

        try:
            response = requests.post(
                f"{self.base_url}/PersonService",
                data=soap_body,
                headers={"Content-Type": "text/xml"},
            )
            return response.text
        except Exception as e:
            return f"<error>{str(e)}</error>"

    def get_person_info(self, cuid: str) -> Dict:
        """Get detailed information about a person via SOAP. Returns structured data."""
        soap_body = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
            <soapenv:Body>
                <getPersonInfo>
                    <uid>{cuid}</uid>
                </getPersonInfo>
            </soapenv:Body>
        </soapenv:Envelope>
        """

        try:
            response = requests.post(
                f"{self.base_url}/PersonService",
                data=soap_body,
                headers={"Content-Type": "text/xml"},
            )

            # Parse XML response into structured data
            parsed_data = self._parse_person_xml(response.text)

            if parsed_data and "error" not in parsed_data:
                return {
                    "success": True,
                    "person": parsed_data,
                    "source": "AnnuaireAgent",
                    "operation": "get_person_info",
                }
            else:
                error_msg = (
                    parsed_data.get("error", "Person not found")
                    if parsed_data
                    else "No response"
                )
                return {
                    "success": False,
                    "error": error_msg,
                    "source": "AnnuaireAgent",
                    "operation": "get_person_info",
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "source": "AnnuaireAgent",
                "operation": "get_person_info",
            }

    def get_mobile_access_info(self, cuid: str) -> str:
        """Get mobile access information for a person via SOAP."""
        soap_body = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
            <soapenv:Body>
                <getPersonMobileAccessInfo>
                    <uid>{cuid}</uid>
                </getPersonMobileAccessInfo>
            </soapenv:Body>
        </soapenv:Envelope>
        """

        try:
            response = requests.post(
                f"{self.base_url}/PersonService",
                data=soap_body,
                headers={"Content-Type": "text/xml"},
            )
            return response.text
        except Exception as e:
            return f"<error>{str(e)}</error>"

    def _parse_person_xml(self, xml_response: str) -> Optional[Dict]:
        """Parse XML response into structured person data"""
        try:
            root = ET.fromstring(xml_response)

            # Find the Person element
            person_elem = root.find(".//Person")
            if person_elem is not None:
                person_data = {}

                # Extract person fields
                for field in [
                    "uid",
                    "givenName",
                    "sn",
                    "mail",
                    "department",
                    "phone",
                    "manager",
                ]:
                    elem = person_elem.find(field)
                    if elem is not None and elem.text:
                        person_data[field] = elem.text

                # Build structured response
                return {
                    "cuid": person_data.get("uid", ""),
                    "name": f"{person_data.get('givenName', '')} {person_data.get('sn', '')}".strip(),
                    "email": person_data.get("mail", ""),
                    "department": person_data.get("department", ""),
                    "phone": person_data.get("phone", ""),
                    "manager": person_data.get("manager", ""),
                }

            # Check for error
            error_elem = root.find(".//Error")
            if error_elem is not None:
                return {"error": error_elem.text}

            return None
        except Exception as e:
            return {"error": f"XML parsing failed: {str(e)}"}

    def search_person(self, query: str) -> Dict:
        """Search for persons based on query via SOAP. Returns structured data."""
        # Build SOAP request with the search query
        soap_body = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
            <soapenv:Body>
                <searchPerson>
                    <query>{query}</query>
                </searchPerson>
            </soapenv:Body>
        </soapenv:Envelope>
        """

        try:
            response = requests.post(
                f"{self.base_url}/PersonService",
                data=soap_body,
                headers={"Content-Type": "text/xml"},
            )

            # Parse XML response into structured data
            parsed_data = self._parse_person_xml(response.text)

            if parsed_data and "error" not in parsed_data:
                return {
                    "success": True,
                    "person": parsed_data,
                    "source": "AnnuaireAgent",
                    "operation": "search_person",
                }
            else:
                error_msg = (
                    parsed_data.get("error", "Person not found")
                    if parsed_data
                    else "No response"
                )
                return {
                    "success": False,
                    "error": error_msg,
                    "source": "AnnuaireAgent",
                    "operation": "search_person",
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "source": "AnnuaireAgent",
                "operation": "search_person",
            }
