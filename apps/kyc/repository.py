from apps.core.repository import BaseRepository
from apps.kyc.models import KycConsultation, KycDossier, KycPiece, StatutKyc


class DossierRepository(BaseRepository[KycDossier]):
    model = KycDossier
    message_introuvable = "Dossier KYC introuvable."

    def queryset(self):
        return super().queryset().select_related("utilisateur").prefetch_related("pieces")

    def get_ou_creer(self, utilisateur, type_dossier: str) -> KycDossier:
        dossier, _ = self.model.objects.get_or_create(utilisateur=utilisateur, type=type_dossier)
        return dossier

    def get_verrouille(self, utilisateur, type_dossier: str) -> KycDossier:
        """À appeler dans un `transaction.atomic()`."""
        self.get_ou_creer(utilisateur, type_dossier)
        return self.model.objects.select_for_update().get(
            utilisateur=utilisateur, type=type_dossier
        )

    def statuts_de(self, utilisateur) -> dict[str, str]:
        return dict(
            self.model.objects.filter(utilisateur=utilisateur).values_list("type", "statut")
        )

    def est_verifie(self, utilisateur, type_dossier: str) -> bool:
        return self.model.objects.filter(
            utilisateur=utilisateur, type=type_dossier, statut=StatutKyc.VERIFIE
        ).exists()

    def lister(self, statut: str | None = None, type_dossier: str | None = None):
        queryset = self.queryset().order_by("soumis_le", "cree_le")
        if statut:
            queryset = queryset.filter(statut=statut)
        if type_dossier:
            queryset = queryset.filter(type=type_dossier)
        return queryset

    def compter_verifies(self, type_dossier: str) -> int:
        return self.model.objects.filter(type=type_dossier, statut=StatutKyc.VERIFIE).count()


class PieceRepository(BaseRepository[KycPiece]):
    model = KycPiece
    message_introuvable = "Pièce KYC introuvable."

    def types_presents(self, dossier: KycDossier) -> set[str]:
        return set(self.filter(dossier=dossier).values_list("type_piece", flat=True))

    def remplacer(self, dossier: KycDossier, type_piece: str, fichier) -> KycPiece:
        ancienne = self.get_or_none(dossier=dossier, type_piece=type_piece)
        if ancienne:
            ancienne.fichier.delete(save=False)
            ancienne.delete()
        return self.create(dossier=dossier, type_piece=type_piece, fichier=fichier)


class ConsultationRepository(BaseRepository[KycConsultation]):
    model = KycConsultation


dossier_repository = DossierRepository()
piece_repository = PieceRepository()
consultation_repository = ConsultationRepository()
