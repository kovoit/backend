import re
from datetime import timedelta

import pytest
from django.core import mail
from freezegun import freeze_time
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts import services
from apps.accounts.models import OtpCode, User
from apps.core.exceptions import DonneesInvalides, TropDeRequetes

pytestmark = pytest.mark.django_db
EMAIL = "Ama.Kodjo@Exemple.tg"


def dernier_code() -> str:
    return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)


def test_demander_envoie_un_code_par_email_et_stocke_seulement_le_hash():
    services.demander_otp(EMAIL)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["ama.kodjo@exemple.tg"]
    otp = OtpCode.objects.get()
    assert dernier_code() not in otp.code_hash


def test_verifier_cree_le_compte_et_renvoie_les_jetons():
    services.demander_otp(EMAIL)

    connexion = services.verifier_otp(EMAIL, dernier_code())

    assert connexion["nouveau_compte"] is True
    assert connexion["access"] and connexion["refresh"]
    utilisateur = User.objects.get(email="ama.kodjo@exemple.tg")
    assert utilisateur.email_verifie
    assert not utilisateur.has_usable_password()


def test_verifier_un_compte_existant(utilisateur):
    services.demander_otp(utilisateur.email)

    connexion = services.verifier_otp(utilisateur.email, dernier_code())

    assert connexion["nouveau_compte"] is False
    assert connexion["utilisateur"] == utilisateur


def test_un_code_ne_sert_qu_une_fois():
    services.demander_otp(EMAIL)
    code = dernier_code()
    services.verifier_otp(EMAIL, code)

    with pytest.raises(services.CodeOtpInvalide):
        services.verifier_otp(EMAIL, code)


def test_mauvais_code_incremente_les_essais_puis_invalide_le_code():
    services.demander_otp(EMAIL)
    bon_code = dernier_code()
    mauvais = "000000" if bon_code != "000000" else "111111"

    for _ in range(5):
        with pytest.raises(services.CodeOtpInvalide):
            services.verifier_otp(EMAIL, mauvais)

    assert OtpCode.objects.get().essais == 5
    with pytest.raises(services.CodeOtpInvalide):
        services.verifier_otp(EMAIL, bon_code)


def test_code_expire():
    with freeze_time("2026-10-08 10:00"):
        services.demander_otp(EMAIL)
    with freeze_time("2026-10-08 10:11"), pytest.raises(services.CodeOtpInvalide):
        services.verifier_otp(EMAIL, dernier_code())


def test_un_nouveau_code_invalide_le_precedent():
    with freeze_time("2026-10-08 10:00"):
        services.demander_otp(EMAIL)
        ancien = dernier_code()
    with freeze_time("2026-10-08 10:02"):
        services.demander_otp(EMAIL)
        nouveau = dernier_code()
        if ancien != nouveau:
            with pytest.raises(services.CodeOtpInvalide):
                services.verifier_otp(EMAIL, ancien)
        assert services.verifier_otp(EMAIL, nouveau)["access"]


def test_renvoi_trop_rapide_refuse():
    with freeze_time("2026-10-08 10:00:00"):
        services.demander_otp(EMAIL)
    with freeze_time("2026-10-08 10:00:30"), pytest.raises(TropDeRequetes):
        services.demander_otp(EMAIL)


def test_maximum_de_codes_par_heure():
    debut = "2026-10-08 10:00"
    for minute in range(5):
        with freeze_time(f"2026-10-08 10:{minute * 2:02d}"):
            services.demander_otp(EMAIL)
    with freeze_time("2026-10-08 10:30"), pytest.raises(TropDeRequetes):
        services.demander_otp(EMAIL)
    with freeze_time(debut) as horloge:
        horloge.move_to("2026-10-08 11:15")
        services.demander_otp(EMAIL)


def test_compte_desactive_refuse(utilisateur):
    utilisateur.is_active = False
    utilisateur.save()
    services.demander_otp(utilisateur.email)

    with pytest.raises(services.CompteDesactive):
        services.verifier_otp(utilisateur.email, dernier_code())


def test_deconnexion_invalide_le_refresh(utilisateur):
    refresh = str(RefreshToken.for_user(utilisateur))

    services.deconnecter(refresh)

    with pytest.raises(DonneesInvalides):
        services.deconnecter(refresh)


def test_code_otp_valable_selon_le_parametre():
    from apps.parametres.services import modifier_param

    modifier_param("otp_validite_min", 30)
    with freeze_time("2026-10-08 10:00"):
        services.demander_otp(EMAIL)
    with freeze_time("2026-10-08 10:00") as horloge:
        horloge.tick(timedelta(minutes=25))
        assert services.verifier_otp(EMAIL, dernier_code())["access"]
