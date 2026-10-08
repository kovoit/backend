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
