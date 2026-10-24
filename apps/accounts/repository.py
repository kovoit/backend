from datetime import datetime

from django.db.models import Q

from apps.accounts.models import OtpCode, StatutCompte, User
from apps.core.repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User
    message_introuvable = "Utilisateur introuvable."

    def get_par_email(self, email: str) -> User | None:
        return self.get_or_none(email=email.strip().lower())

    def creer(self, email: str, **champs) -> User:
        return User.objects.create_user(email=email, **champs)

    def get_ou_creer(self, email: str) -> tuple[User, bool]:
        utilisateur = self.get_par_email(email)
        if utilisateur:
            return utilisateur, False
        return self.creer(email), True

    def lister(self, recherche: str | None = None, statut: str | None = None):
        queryset = self.queryset().order_by("-cree_le")
        if recherche:
            queryset = queryset.filter(
                Q(email__icontains=recherche)
                | Q(nom__icontains=recherche)
                | Q(prenom__icontains=recherche)
                | Q(telephone__icontains=recherche)
            )
        if statut:
            queryset = queryset.filter(statut_compte=statut)
        return queryset

    def suspensions_expirees(self, maintenant: datetime):
        return self.filter(statut_compte=StatutCompte.SUSPENDU, suspendu_jusqu_au__lte=maintenant)

    def changer_mot_de_passe(self, utilisateur: User, mot_de_passe: str) -> User:
        utilisateur.set_password(mot_de_passe)
        utilisateur.save(update_fields=["password"])
        return utilisateur

    def revoquer_sessions(self, utilisateur: User) -> None:
        """Met en liste noire tous les refresh tokens encore valides de l'utilisateur."""
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        for jeton in OutstandingToken.objects.filter(user=utilisateur):
            BlacklistedToken.objects.get_or_create(token=jeton)

    def anonymiser(self, utilisateur: User, email: str) -> User:
        """Compte supprimé : plus aucune donnée d'identité ni moyen de connexion."""
        if utilisateur.photo:
            utilisateur.photo.delete(save=False)
        for vehicule in utilisateur.vehicules.all():
            if vehicule.photo:
                vehicule.photo.delete(save=False)
                vehicule.save(update_fields=["photo"])
        utilisateur.email = email
        utilisateur.nom, utilisateur.prenom = "Compte", "supprimé"
        utilisateur.telephone = ""
        utilisateur.is_active = False
        utilisateur.email_verifie = False
        utilisateur.set_unusable_password()
        utilisateur.save()
        return utilisateur

    def admins_actifs(self):
        return self.filter(is_staff=True, is_active=True)

    def groupes_parmi(self, utilisateur: User, noms) -> set[str]:
        return set(utilisateur.groups.filter(name__in=list(noms)).values_list("name", flat=True))

    def compter(self, **filtres) -> int:
        return self.filter(**filtres).count()


class OtpRepository(BaseRepository[OtpCode]):
    model = OtpCode

    def dernier_envoye(self, email: str) -> OtpCode | None:
        return self.filter(email=email).order_by("-cree_le").first()

    def nombre_envoyes_depuis(self, email: str, depuis: datetime) -> int:
        return self.filter(email=email, cree_le__gte=depuis).count()

    def invalider_actifs(self, email: str) -> None:
        self.filter(email=email, utilise=False).update(utilise=True)

    def dernier_actif_verrouille(self, email: str, maintenant: datetime) -> OtpCode | None:
        """À appeler dans un `transaction.atomic()`."""
        return (
            self.queryset()
            .select_for_update()
            .filter(email=email, utilise=False, expire_le__gt=maintenant)
            .order_by("-cree_le")
            .first()
        )


user_repository = UserRepository()
otp_repository = OtpRepository()
