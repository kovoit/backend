"""Rôles du back-office : groupes Django attribués dans le Django admin par un superutilisateur.

- superutilisateur (is_staff) : tous les rôles, avec ou sans groupe ;
- admin (is_staff) : uniquement les domaines de ses rôles ;
- admin SANS aucun rôle : tableau de bord et consultation des paramètres seulement.
Tous les admins voient le tableau de bord et consultent les paramètres. La migration
accounts/0006 a donné les quatre rôles aux admins existants qui n'en avaient aucun.
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

    return user_repository.groupes_parmi(utilisateur, ROLES)
