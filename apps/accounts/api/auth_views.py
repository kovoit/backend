"""Connexion à l'application par e-mail + mot de passe (F-070 à F-073, contrat M-004 T0).

Routes publiques, limite DRF `anon` (60/min) sauf `auth/connexion/` : 5/min par IP.
"""

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts import services
from apps.accounts.api import auth_serializers as a
from apps.accounts.api.serializers import ConnexionSerializer
from apps.core.api.reponses import succes

TAG = "authentification"
MESSAGE_RENVOI = (
    "Si un compte attend la vérification de cette adresse, un nouveau code vient d'y être envoyé."
)
MESSAGE_OUBLIE = (
    "Si cette adresse correspond à un compte, un code de réinitialisation vient d'y être envoyé."
)


class _Publique(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]


def _lire(serializer_class, request) -> dict:
    entree = serializer_class(data=request.data)
    entree.is_valid(raise_exception=True)
    return entree.validated_data


class InscriptionVue(_Publique):
    @extend_schema(
        tags=[TAG],
        summary="Créer son compte (aucun jeton : un code de vérification part à l'adresse)",
        description="Erreurs, dans l'ordre : 400 DONNEES_INVALIDES, 400 TELEPHONE_INVALIDE, "
        "400 MOT_DE_PASSE_FAIBLE, 409 EMAIL_DEJA_UTILISE.",
        request=a.InscriptionSerializer,
        responses={201: a.CodeEnvoyeSerializer},
    )
    def post(self, request):
        donnees = _lire(a.InscriptionSerializer, request)
        donnees.pop("cgu_acceptees")
        envoi = services.inscrire(**donnees)
        return succes(
            "Compte créé. Saisissez le code envoyé à votre adresse e-mail.", envoi, status=201
        )


class InscriptionVerificationVue(_Publique):
    @extend_schema(
        tags=[TAG],
        summary="Vérifier son adresse e-mail par code et ouvrir la session",
        description="400 CODE_OTP_INVALIDE : code faux, expiré, déjà utilisé, essais épuisés, "
        "compte inconnu, désactivé ou déjà vérifié.",
        request=a.VerificationEmailSerializer,
        responses=ConnexionSerializer,
    )
    def post(self, request):
        session = services.verifier_email(**_lire(a.VerificationEmailSerializer, request))
        return succes("Adresse e-mail vérifiée.", ConnexionSerializer(session).data)


class RenvoyerCodeVue(_Publique):
    @extend_schema(
        tags=[TAG],
        summary="Renvoyer le code de vérification (même réponse pour toute adresse)",
        description="429 TROP_DE_REQUETES : compte en attente de vérification, dans le délai "
        "de renvoi ou au plafond horaire.",
        request=a.EmailSerializer,
        responses=a.CodeEnvoyeSerializer,
    )
    def post(self, request):
        envoi = services.renvoyer_code(_lire(a.EmailSerializer, request)["email"])
        return succes(MESSAGE_RENVOI, envoi)


class ConnexionVue(_Publique):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "connexion"

    @extend_schema(
        tags=[TAG],
        summary="Se connecter par e-mail et mot de passe",
        description="401 IDENTIFIANTS_INVALIDES (même réponse pour adresse inconnue, mauvais "
        "mot de passe, compte désactivé) ; 403 EMAIL_NON_VERIFIE (bon mot de passe, un code "
        "est renvoyé hors délai) ; 429 TROP_DE_REQUETES (5/min par IP).",
        request=a.ConnexionApplicationSerializer,
        responses=ConnexionSerializer,
    )
    def post(self, request):
        session = services.connecter(**_lire(a.ConnexionApplicationSerializer, request))
        return succes("Connexion réussie.", ConnexionSerializer(session).data)


class MotDePasseOublieVue(_Publique):
    @extend_schema(
        tags=[TAG],
        summary="Mot de passe oublié : code par e-mail (même réponse pour toute adresse)",
        description="Aucun code pour une adresse inconnue, un compte désactivé ou un "
        "administrateur. 429 TROP_DE_REQUETES : compte éligible à la limite.",
        request=a.EmailSerializer,
        responses=a.CodeEnvoyeSerializer,
    )
    def post(self, request):
        envoi = services.demander_code_reinitialisation(_lire(a.EmailSerializer, request)["email"])
        return succes(MESSAGE_OUBLIE, envoi)


class ReinitialiserParCodeVue(_Publique):
    @extend_schema(
        tags=[TAG],
        summary="Choisir un nouveau mot de passe avec le code reçu (aucun jeton émis)",
        description="400 MOT_DE_PASSE_FAIBLE (contrôlé avant le code, qui reste valable) ; "
        "400 CODE_OTP_INVALIDE. Toutes les sessions ouvertes sont révoquées.",
        request=a.ReinitialisationParCodeSerializer,
        responses={200: None},
    )
    def post(self, request):
        services.reinitialiser_par_code(**_lire(a.ReinitialisationParCodeSerializer, request))
        return succes("Mot de passe modifié. Connectez-vous avec votre nouveau mot de passe.")
