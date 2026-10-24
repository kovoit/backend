"""Rôles du back-office : groupes Django attribués par un superutilisateur (Django admin).

- superutilisateur, ou admin (is_staff) SANS aucun rôle : administrateur général, accès à tout
  (les comptes existants ne perdent aucun accès) ;
- admin avec un ou plusieurs rôles : limité à ces domaines.
Tous les admins voient le tableau de bord et consultent les paramètres.
"""

MODERATION = "moderation"  # KYC, utilisateurs, trajets, réservations, signalements et litiges
FINANCE = "finance"  # transactions et retraits à verser
AUDIT = "audit"  # journal d'audit et export
PARAMETRES = "parametres"  # modification des paramètres (prix, commission, règles)

ROLES = {
    MODERATION: "Modération",
    FINANCE: "Finance",
    AUDIT: "Audit",
    PARAMETRES: "Paramètres",
}


def roles_de(utilisateur) -> set[str]:
    """Rôles effectifs d'un admin (ensemble vide si ce n'est pas un admin actif)."""
    if not (utilisateur and utilisateur.is_authenticated and utilisateur.is_staff):
        return set()
    if utilisateur.is_superuser:
        return set(ROLES)
    from apps.accounts.repository import user_repository

    attribues = user_repository.groupes_parmi(utilisateur, ROLES)
    return attribues or set(ROLES)
