"""
Agent Provisionning - Fournir les équipements physiques nécessaires au collaborateur

Objectif: Fournir les équipements physiques nécessaires au collaborateur

Tâches:
- Vérifier l'éligibilité du collaborateur à l'équipement métier (offre A) - PROVISIONNING / 26E
- Sélectionner le modèle précis attribué au collaborateur - PROVISIONNING / SIGALE
- Commander le produit - SIGALE
- Notifier le manager des statuts de la livraison - FRONT Dédié / SIGALE
- Demander une validation humaine d'éligibilité - FRONT Dédié
- Demander une validation humaine d'attribution du modèle - FRONT Dédié
- Changer le statut du matériel - 26E

Systèmes intégrés:
- PROVISIONNING: Gestion des modèles attribués au collaborateur en fonction des règles d'attribution
- SIGALE: Gestion des commandes et de la logistique d'approvisionnement du matériel
- 26E: Référentiel de tous les matériels (modification des statuts)
- FRONT Dédié: Interface pour les validations humaines
"""

import requests
from typing import Dict, List, Optional
from framework.actor.base_actor import Actor
from framework.types import LLMConfig


class ProvisionningAgent(Actor):
    """
    ProvisionningActor – Pilot migration to JAF Actor model.

    IMPORTANT
    - Business logic unchanged
    - Only framework wrapping added (Actor, configure, tools, typing)
    """

    def __init__(self, base_url: str = "http://localhost:8089"):
        super().__init__()

        self.base_url = base_url
        service_base = (
            f"{base_url}/mock" if not base_url.endswith("/mock") else base_url
        )

        self.endpoints = {
            "provisionning": f"{service_base}/provisionning",
            "sigale": f"{service_base}/sigale",
            "vingt_six_e": f"{service_base}/26e",
            "front_dedie": f"{service_base}/front-dedie",
        }

        self.agent_config = {
            "default_validation_priority": "normale",
            "default_order_type": "provisioning_onboarding",
            "restitution_order_type": "restitution_offboarding",
            "replacement_order_type": "replacement_defective",
            "status_change_motif": "attribution_provisioning",
        }

        # HTTP session (performance + consistency)
        self.http = requests.Session()
        self.http.headers.update({"Content-Type": "application/json"})

    # ==========================================================================
    # ACTOR CONFIGURATION (JAF)
    # ==========================================================================

    def configure(self) -> None:
        """
        Actor configuration hook (called once by ActorRegistry).
        """
        self.name = "ProvisionningActor"
        self.description = (
            "Fournir les équipements physiques nécessaires au collaborateur"
        )
        self.goal = (
            "Gérer l'approvisionnement en équipements physiques pour les collaborateurs"
        )

        self.tools = [
            self.verifier_eligibilite_collaborateur_offre_A,
            self.selectionner_modele_attribue,
            self.commander_produit,
            self.notifier_manager_statut_livraison,
            self.suivi_commande,
            self.demander_validation_humaine_eligibilite,
            self.demander_validation_humaine_attribution_modele,
            self.changer_statut_materiel,
            self.recuperer_materiel,
            self.creer_demande_restitution,
            self.get_material_status_in_parc,
            self.workflow_onboarding_avec_pc,
            self.workflow_offboarding_avec_pc,
            self.workflow_remplacement_pc_defectueux,
            self.provision_equipment_workflow,
        ]

        # Deterministic actor (no LLM)
        self.llm_config: Optional[LLMConfig] = None

    # ==========================================================================
    # TASK 1 – Eligibility
    # ==========================================================================

    def verifier_eligibilite_collaborateur_offre_A(self, cuid: str) -> Dict:
        try:
            response = self.http.get(
                f"{self.endpoints['provisionning']}/eligibilite/{cuid}", timeout=5
            )
            if response.ok:
                eligibility_data = response.json()

                equipment_response = self.http.get(
                    f"{self.endpoints['vingt_six_e']}/materiel/status/{cuid}", timeout=5
                )
                if equipment_response.ok:
                    equipment_data = equipment_response.json()
                    return {
                        "eligible": eligibility_data.get("eligible", False),
                        "raisons": eligibility_data.get("raisons", []),
                        "materiel_existant": equipment_data.get(
                            "materiel_existant", False
                        ),
                        "details": {
                            "statut": eligibility_data.get("statut"),
                            "contrat": eligibility_data.get("contrat"),
                            "metier": eligibility_data.get("metier"),
                            "entite": eligibility_data.get("entite"),
                            "materiel_actuel": equipment_data.get(
                                "materiel_actuel", []
                            ),
                        },
                    }

            return {"eligible": False, "error": "eligibility_check_failed"}

        except Exception as e:
            return {"eligible": False, "error": str(e)}

    # ==========================================================================
    # TASK 2 – Model selection
    # ==========================================================================

    def selectionner_modele_attribue(self, cuid: str) -> Dict:
        try:
            response = self.http.get(
                f"{self.endpoints['provisionning']}/modeles/attribution/{cuid}",
                timeout=5,
            )
            if response.ok:
                attribution_data = response.json()

                sigale_response = self.http.get(
                    f"{self.endpoints['sigale']}/modeles/disponibles", timeout=5
                )
                if sigale_response.ok:
                    available_models = sigale_response.json()

                    return {
                        "modele_attribue": attribution_data.get("modele_recommande"),
                        "generation": attribution_data.get("generation"),
                        "justification": attribution_data.get("justification"),
                        "modeles_alternatifs": available_models.get("alternatives", []),
                        "stock_disponible": available_models.get("stock", 0),
                    }

            return {"error": "model_selection_failed"}

        except Exception as e:
            return {"error": str(e)}

    # ==========================================================================
    # TASK 3 – Order
    # ==========================================================================

    def commander_produit(self, cuid: str, modele: str, adresse_livraison: str) -> Dict:
        payload = {
            "cuid": cuid,
            "modele": modele,
            "adresse_livraison": adresse_livraison,
            "type_commande": self.agent_config["default_order_type"],
        }

        try:
            response = self.http.post(
                f"{self.endpoints['sigale']}/commandes",
                json=payload,
                timeout=5,
            )
            if response.ok:
                data = response.json()
                return {
                    "numero_commande": data.get("numero_commande"),
                    "statut": data.get("statut"),
                    "date_livraison_prevue": data.get("date_livraison_prevue"),
                    "transporteur": data.get("transporteur"),
                    "numero_suivi": data.get("numero_suivi"),
                }

            return {"error": "order_failed", "status_code": response.status_code}

        except Exception as e:
            return {"error": str(e)}

    # ==========================================================================
    # TASK 4 – Notification
    # ==========================================================================

    def notifier_manager_statut_livraison(
        self, cuid: str, numero_commande: str, manager_cuid: str
    ) -> Dict:
        try:
            response = self.http.get(
                f"{self.endpoints['sigale']}/commandes/{numero_commande}/statut",
                timeout=5,
            )
            if response.ok:
                statut_data = response.json()

                payload = {
                    "destinataire_cuid": manager_cuid,
                    "collaborateur_cuid": cuid,
                    "numero_commande": numero_commande,
                    "statut": statut_data.get("statut"),
                    "message": statut_data.get("statut_detaille"),
                }

                notif = self.http.post(
                    f"{self.endpoints['front_dedie']}/notifications/manager",
                    json=payload,
                    timeout=5,
                )

                if notif.ok:
                    return {
                        "notification_envoyee": True,
                        "statut": statut_data.get("statut"),
                    }

            return {"error": "notification_failed"}

        except Exception as e:
            return {"error": str(e)}

    # ==========================================================================
    # SUPPORT METHODS (unchanged logic)
    # ==========================================================================

    def suivi_commande(self, numero_commande: str) -> Dict:
        try:
            response = self.http.get(
                f"{self.endpoints['sigale']}/commandes/{numero_commande}", timeout=5
            )
            return response.json() if response.ok else {"error": "order_not_found"}
        except Exception as e:
            return {"error": str(e)}

    def demander_validation_humaine_eligibilite(
        self, cuid: str, raisons_rejet: List[str] = None
    ) -> Dict:
        payload = {
            "cuid": cuid,
            "type_validation": "eligibilite",
            "raisons_rejet": raisons_rejet or [],
            "demandeur": self.name,
            "priorite": self.agent_config["default_validation_priority"],
        }
        try:
            response = self.http.post(
                f"{self.endpoints['front_dedie']}/validations/eligibilite",
                json=payload,
                timeout=5,
            )
            return response.json() if response.ok else {"error": "validation_failed"}
        except Exception as e:
            return {"error": str(e)}

    def demander_validation_humaine_attribution_modele(
        self, cuid: str, modele_propose: str, motif: str = ""
    ) -> Dict:
        payload = {
            "cuid": cuid,
            "type_validation": "attribution_modele",
            "modele_propose": modele_propose,
            "motif_validation": motif,
            "demandeur": self.name,
        }
        try:
            response = self.http.post(
                f"{self.endpoints['front_dedie']}/validations/attribution",
                json=payload,
                timeout=5,
            )
            return response.json() if response.ok else {"error": "validation_failed"}
        except Exception as e:
            return {"error": str(e)}

    def changer_statut_materiel(
        self,
        numero_serie: str,
        ancien_statut: str,
        nouveau_statut: str,
        cuid: str = None,
    ) -> Dict:
        payload = {
            "numero_serie": numero_serie,
            "ancien_statut": ancien_statut,
            "nouveau_statut": nouveau_statut,
            "cuid_attributaire": cuid,
            "motif": self.agent_config["status_change_motif"],
        }
        try:
            response = self.http.put(
                f"{self.endpoints['vingt_six_e']}/materiel/{numero_serie}/statut",
                json=payload,
                timeout=5,
            )
            return response.json() if response.ok else {"error": "status_change_failed"}
        except Exception as e:
            return {"error": str(e)}

    def recuperer_materiel(self, cuid: str) -> Dict:
        try:
            response = self.http.get(
                f"{self.endpoints['vingt_six_e']}/materiel/utilisateur/{cuid}",
                timeout=5,
            )
            return response.json() if response.ok else {"error": "equipment_not_found"}
        except Exception as e:
            return {"error": str(e)}

    def creer_demande_restitution(
        self, cuid: str, numero_serie: str, adresse_retour: str
    ) -> Dict:
        payload = {
            "cuid": cuid,
            "numero_serie": numero_serie,
            "adresse_retour": adresse_retour,
            "type_demande": self.agent_config["restitution_order_type"],
        }
        try:
            response = self.http.post(
                f"{self.endpoints['sigale']}/restitutions",
                json=payload,
                timeout=5,
            )
            return response.json() if response.ok else {"error": "restitution_failed"}
        except Exception as e:
            return {"error": str(e)}

    def get_material_status_in_parc(self, numero_serie: str) -> Dict:
        try:
            response = self.http.get(
                f"{self.endpoints['vingt_six_e']}/materiel/{numero_serie}",
                timeout=5,
            )
            return response.json() if response.ok else {"error": "material_not_found"}
        except Exception as e:
            return {"error": str(e)}

    # ============================================================================
    # BUSINESS SCENARIO WORKFLOWS
    # ============================================================================

    def workflow_onboarding_avec_pc(
        self,
        cuid: str,
        manager_cuid: str,
        adresse_livraison: str,
        force_validation: bool = False,
    ) -> Dict:
        """
        Scenario: Onboarding d'un collaborateur avec provisionning d'un PC

        Steps:
        1. Validation de l'éligibilité au PC et si KO demande d'une validation humaine
        2. Commande du PC et suivi de la commande
        3. Communication mail au collaborateur de la dispo de son PC
        """
        workflow_result = {
            "scenario": "onboarding_avec_pc",
            "cuid": cuid,
            "workflow_status": "started",
            "steps": {},
        }

        # Step 1: Eligibility check
        eligibility = self.verifier_eligibilite_collaborateur_offre_A(cuid)
        workflow_result["steps"]["eligibility_check"] = eligibility

        if not eligibility.get("eligible", False) and not force_validation:
            # Request human validation
            validation = self.demander_validation_humaine_eligibilite(
                cuid, eligibility.get("raisons", [])
            )
            workflow_result["steps"]["human_validation_requested"] = validation
            workflow_result["workflow_status"] = "pending_human_validation"
            return workflow_result

        # Step 2: Model selection and order
        model_selection = self.selectionner_modele_attribue(cuid)
        workflow_result["steps"]["model_selection"] = model_selection

        if model_selection.get("error"):
            workflow_result["workflow_status"] = "error_model_selection"
            return workflow_result

        order = self.commander_produit(
            cuid, model_selection.get("modele_attribue", ""), adresse_livraison
        )
        workflow_result["steps"]["order_placed"] = order

        # Step 3: Manager notification
        if not order.get("error"):
            notification = self.notifier_manager_statut_livraison(
                cuid, order.get("numero_commande", ""), manager_cuid
            )
            workflow_result["steps"]["manager_notification"] = notification
            workflow_result["workflow_status"] = "completed"
        else:
            workflow_result["workflow_status"] = "error_order_placement"

        return workflow_result

    def workflow_offboarding_avec_pc(
        self, cuid: str, numero_serie: str = None, adresse_retour: str = None
    ) -> Dict:
        """
        Scenario: Offboarding d'un collaborateur disposant d'un PC et d'une appli métier

        Steps:
        1. Création d'une commande de restitution du PC du collaborateur et suivi de cette commande
        2. Suppression de l'identité et des comptes mail et eBuro du collaborateur (handled by Identités agent)
        """
        workflow_result = {
            "scenario": "offboarding_avec_pc",
            "cuid": cuid,
            "workflow_status": "started",
            "steps": {},
        }

        # Step 1: Get user equipment if not provided
        if not numero_serie:
            equipment = self.recuperer_materiel(cuid)
            workflow_result["steps"]["equipment_check"] = equipment

            if equipment.get("error") or not equipment.get("materiel"):
                workflow_result["workflow_status"] = "no_equipment_found"
                return workflow_result

            numero_serie = equipment["materiel"][0].get("numero_serie", "")

        # Step 2: Create restitution request
        if numero_serie and adresse_retour:
            restitution = self.creer_demande_restitution(
                cuid, numero_serie, adresse_retour
            )
            workflow_result["steps"]["restitution_created"] = restitution

            if not restitution.get("error"):
                # Step 3: Update material status to "en_retour"
                status_change = self.changer_statut_materiel(
                    numero_serie, "en_parc", "en_retour", cuid
                )
                workflow_result["steps"]["status_updated"] = status_change
                workflow_result["workflow_status"] = "completed"
            else:
                workflow_result["workflow_status"] = "error_restitution"
        else:
            workflow_result["workflow_status"] = "missing_parameters"
            workflow_result["error"] = "numero_serie and adresse_retour required"

        return workflow_result

    def workflow_remplacement_pc_defectueux(
        self,
        cuid: str,
        numero_serie_defectueux: str,
        adresse_livraison: str,
        manager_cuid: str = None,
    ) -> Dict:
        """
        Scenario: Remplacement d'un PC défectueux

        Steps:
        1. Récupération des infos sur le PC à remplacer
        2. Création et suivi d'une commande de restitution du PC défectueux
        3. Création et suivi d'une commande d'un nouveau PC
        4. Communication mail au collaborateur sur le remplacement de son PC
        """
        workflow_result = {
            "scenario": "remplacement_pc_defectueux",
            "cuid": cuid,
            "workflow_status": "started",
            "steps": {},
        }

        # Step 1: Get info about defective PC
        pc_info = self.get_material_status_in_parc(numero_serie_defectueux)
        workflow_result["steps"]["defective_pc_info"] = pc_info

        if pc_info.get("error"):
            workflow_result["workflow_status"] = "error_pc_info"
            return workflow_result

        # Step 2: Create restitution request for defective PC
        restitution = self.creer_demande_restitution(
            cuid, numero_serie_defectueux, adresse_livraison
        )
        workflow_result["steps"]["defective_pc_return"] = restitution

        # Step 3: Change status of defective PC
        if not restitution.get("error"):
            status_change_defective = self.changer_statut_materiel(
                numero_serie_defectueux, "en_parc", "defectueux_en_retour", cuid
            )
            workflow_result["steps"][
                "defective_status_updated"
            ] = status_change_defective

        # Step 4: Order replacement PC (use replacement order type)
        self.agent_config["default_order_type"] = self.agent_config[
            "replacement_order_type"
        ]

        # Get model for replacement (same as defective or upgraded)
        modele_remplacement = pc_info.get(
            "modele", "Dell Latitude 7420"
        )  # Fallback model

        replacement_order = self.commander_produit(
            cuid, modele_remplacement, adresse_livraison
        )
        workflow_result["steps"]["replacement_order"] = replacement_order

        # Step 5: Notify manager if provided
        if manager_cuid and not replacement_order.get("error"):
            notification = self.notifier_manager_statut_livraison(
                cuid, replacement_order.get("numero_commande", ""), manager_cuid
            )
            workflow_result["steps"]["manager_notification"] = notification

        # Reset order type to default
        self.agent_config["default_order_type"] = "provisioning_onboarding"

        workflow_result["workflow_status"] = (
            "completed"
            if not replacement_order.get("error")
            else "error_replacement_order"
        )
        return workflow_result

    # Legacy workflow kept untouched for backward compatibility
    def provision_equipment_workflow(
        self, cuid: str, manager_cuid: str, adresse_livraison: str
    ) -> Dict:
        return self.workflow_onboarding_avec_pc(cuid, manager_cuid, adresse_livraison)
