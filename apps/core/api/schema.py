"""Post-traitement OpenAPI : documente l'enveloppe { statut, message, reponse } partout."""

REF_ECHEC = "#/components/schemas/ReponseEchec"

# Noms explicites des énumérations (plusieurs modèles ont des champs « statut » ou « type »)
ENUM_NAME_OVERRIDES = {
    # Mêmes choix (passager / conducteur) pour le mode actif et le type de dossier KYC
    "RoleEnum": "apps.accounts.models.ModeActif",
    "StatutCompteEnum": "apps.accounts.models.StatutCompte",
    "StatutKycEnum": "apps.kyc.models.StatutKyc",
    "StatutTrajetEnum": "apps.trajets.models.StatutTrajet",
    "StatutReservationEnum": "apps.reservations.models.StatutReservation",
    "StatutSignalementEnum": "apps.confiance.models.StatutSignalement",
    "TypeTransactionEnum": "apps.portefeuille.models.TypeTransaction",
    "StatutTransactionEnum": "apps.portefeuille.models.StatutTransaction",
    "MoyenPaiementEnum": "apps.portefeuille.models.MoyenPaiement",
    "RoleAuditEnum": "apps.audit.models.Role",
    "CategorieAuditEnum": "apps.audit.models.Categorie",
    "ResultatAuditEnum": "apps.audit.models.Resultat",
    "GraviteAuditEnum": "apps.audit.models.Gravite",
    "CanalAuditEnum": "apps.audit.models.Canal",
}

# Réglages drf-spectacular (repris par SPECTACULAR_SETTINGS dans kovoit/settings.py)
REGLAGES_SPECTACULAR = {
    "TITLE": "API Kovoit",
    "DESCRIPTION": (
        "API backend Kovoit (covoiturage urbain à Lomé). Toutes les réponses suivent "
        "l'enveloppe { statut: success | failed, message, reponse }."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": ENUM_NAME_OVERRIDES,
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "apps.core.api.schema.envelopper_reponses",
    ],
}

SCHEMA_ECHEC = {
    "type": "object",
    "required": ["statut", "message", "reponse"],
    "properties": {
        "statut": {"type": "string", "enum": ["failed"]},
        "message": {"type": "string"},
        "reponse": {
            "type": "object",
            "required": ["code"],
            "properties": {
                "code": {"type": "string", "example": "DONNEES_INVALIDES"},
                "erreurs": {"type": "object", "nullable": True},
            },
        },
    },
}


def _enveloppe_succes(schema: dict) -> dict:
    return {
        "type": "object",
        "required": ["statut", "message", "reponse"],
        "properties": {
            "statut": {"type": "string", "enum": ["success"]},
            "message": {"type": "string"},
            "reponse": schema,
        },
    }


def envelopper_reponses(result, generator, request, public):
    result.setdefault("components", {}).setdefault("schemas", {})["ReponseEchec"] = SCHEMA_ECHEC

    for chemin in result.get("paths", {}).values():
        for operation in chemin.values():
            if not isinstance(operation, dict) or "responses" not in operation:
                continue
            for code, reponse in operation["responses"].items():
                if not str(code).startswith("2"):
                    continue
                contenus = reponse.setdefault("content", {})
                if not contenus:  # succès sans données : reponse = null
                    contenus["application/json"] = {"schema": {"nullable": True}}
                contenu = contenus.get("application/json")
                if contenu:
                    contenu["schema"] = _enveloppe_succes(contenu.get("schema", {}))
            operation["responses"].setdefault(
                "default",
                {
                    "description": "Erreur (enveloppe failed)",
                    "content": {"application/json": {"schema": {"$ref": REF_ECHEC}}},
                },
            )
    return result
