from apps.core.exceptions import Conflit, DonneesInvalides
from apps.vehicules.models import TypeVehicule, Vehicule
from apps.vehicules.repository import vehicule_repository

CHAMPS_MODIFIABLES = {
    "type_vehicule",
    "marque",
    "modele",
    "couleur",
    "immatriculation",
    "nb_places",
    "photo",
}


def _normaliser_immatriculation(valeur: str) -> str:
    return "".join(valeur.split()).upper()


def _verifier(donnees: dict, vehicule_id=None) -> dict:
    if "immatriculation" in donnees:
        donnees["immatriculation"] = _normaliser_immatriculation(donnees["immatriculation"])
        if vehicule_repository.immatriculation_prise(donnees["immatriculation"], vehicule_id):
            raise Conflit(
                "Cette immatriculation est déjà enregistrée.", code="IMMATRICULATION_EXISTANTE"
            )
    if donnees.get("type_vehicule") == TypeVehicule.MOTO and donnees.get("nb_places", 2) != 2:
        raise DonneesInvalides("Une moto compte 2 places (conducteur compris).")
    return donnees


def mes_vehicules(utilisateur):
    return vehicule_repository.de(utilisateur)


def get_vehicule(utilisateur, vehicule_id) -> Vehicule:
    return vehicule_repository.get_de(utilisateur, vehicule_id)


def declarer(utilisateur, **donnees) -> Vehicule:
    donnees = _verifier({k: v for k, v in donnees.items() if k in CHAMPS_MODIFIABLES})
    return vehicule_repository.create(proprietaire=utilisateur, **donnees)


def modifier(utilisateur, vehicule_id, **donnees) -> Vehicule:
    vehicule = vehicule_repository.get_de(utilisateur, vehicule_id)
    donnees = {k: v for k, v in donnees.items() if k in CHAMPS_MODIFIABLES}
    donnees.setdefault("type_vehicule", vehicule.type_vehicule)
    donnees.setdefault("nb_places", vehicule.nb_places)
    donnees = _verifier(donnees, vehicule.id)
    return vehicule_repository.update(vehicule, **donnees)


def supprimer(utilisateur, vehicule_id) -> None:
    vehicule = vehicule_repository.get_de(utilisateur, vehicule_id)
    if vehicule_repository.a_des_trajets(vehicule):
        raise Conflit(
            "Ce véhicule est lié à des trajets et ne peut pas être supprimé.",
            code="VEHICULE_UTILISE",
        )
    vehicule_repository.delete(vehicule)
