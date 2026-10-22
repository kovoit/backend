from rest_framework import serializers

from apps.accounts.repository import user_repository
from apps.audit import services
from apps.audit.catalogue import ACTIONS
from apps.audit.models import Canal, Categorie, EvenementAudit, Gravite, Resultat, Role
from apps.dashboard.services import PERIODES


class ActeurSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    prenom = serializers.CharField(allow_null=True)
    nom = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    supprime = serializers.BooleanField(help_text="Compte supprimé depuis l'événement")


class EvenementListeSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        evenements = list(data)
        # Une seule requête pour les acteurs de la page (pas de N+1)
        self.context["acteurs"] = services.acteurs(evenements)
        return super().to_representation(evenements)


class EvenementSerializer(serializers.ModelSerializer):
    libelle = serializers.SerializerMethodField()
    acteur = serializers.SerializerMethodField()

    class Meta:
        model = EvenementAudit
        list_serializer_class = EvenementListeSerializer
        fields = [
            "id",
            "survenu_le",
            "enregistre_le",
            "categorie",
            "action",
            "libelle",
            "resultat",
            "gravite",
            "canal",
            "acteur",
            "acteur_role",
            "ressource_type",
            "ressource_id",
            "code_motif",
            "request_id",
            "details",
            "changements",
        ]

    def get_libelle(self, evenement) -> str:
        definition = ACTIONS.get(evenement.action)
        return definition.libelle if definition else evenement.action

    @staticmethod
    def _acteur(identifiant, utilisateur) -> dict:
        if utilisateur is None:
            return {"id": identifiant, "prenom": None, "nom": None, "email": None, "supprime": True}
        return {
            "id": identifiant,
            "prenom": utilisateur.prenom,
            "nom": utilisateur.nom,
            "email": utilisateur.email,
            "supprime": False,
        }

    def get_acteur(self, evenement) -> ActeurSerializer(allow_null=True):  # type: ignore[valid-type]
        if evenement.acteur_id is None:
            return None
        if "acteurs" in self.context:
            utilisateur = self.context["acteurs"].get(evenement.acteur_id)
        else:
            utilisateur = user_repository.get_or_none(id=evenement.acteur_id)
        return self._acteur(evenement.acteur_id, utilisateur)


class FiltresSerializer(serializers.Serializer):
    debut = serializers.DateTimeField(required=False)
    fin = serializers.DateTimeField(required=False)
    acteur = serializers.UUIDField(required=False)
    utilisateur = serializers.UUIDField(required=False, help_text="Actions de / sur ce compte")
    role = serializers.ChoiceField(choices=Role.choices, required=False)
    categorie = serializers.ChoiceField(choices=Categorie.choices, required=False)
    action = serializers.ChoiceField(choices=sorted(ACTIONS), required=False)
    resultat = serializers.ChoiceField(choices=Resultat.choices, required=False)
    canal = serializers.ChoiceField(choices=Canal.choices, required=False)
    gravite = serializers.ChoiceField(choices=Gravite.choices, required=False)
    ressource_type = serializers.CharField(max_length=32, required=False)
    ressource_id = serializers.CharField(max_length=64, required=False)
    correlation = serializers.CharField(max_length=32, required=False)
    recherche = serializers.CharField(max_length=100, required=False)

    def validate(self, attrs):
        if attrs.get("debut") and attrs.get("fin") and attrs["debut"] > attrs["fin"]:
            raise serializers.ValidationError({"fin": "La fin doit suivre le début."})
        return attrs


class FluxEntreeSerializer(FiltresSerializer):
    depuis = serializers.DateTimeField(help_text="Date du plus récent événement déjà reçu")


class FluxSerializer(serializers.Serializer):
    evenements = EvenementSerializer(many=True)
    tronque = serializers.BooleanField(
        help_text="Plus d'événements que la limite : recharger la liste paginée"
    )
    serveur_le = serializers.DateTimeField()


class StatsEntreeSerializer(serializers.Serializer):
    periode = serializers.ChoiceField(choices=list(PERIODES), default="7j")


class StatsSerializer(serializers.Serializer):
    debut = serializers.DateTimeField()
    fin = serializers.DateTimeField()
    total = serializers.IntegerField()
    metier_succes = serializers.IntegerField()
    metier_refus = serializers.IntegerField(help_text="Refus métier et échecs")
    securite = serializers.IntegerField()
    securite_refus = serializers.IntegerField()
    technique = serializers.IntegerField()
    admin = serializers.IntegerField()
    utilisateurs_actifs = serializers.IntegerField(
        help_text="Passagers et conducteurs ayant au moins un événement sur la période"
    )
    derniere_activite = serializers.DateTimeField(allow_null=True)
