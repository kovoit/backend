"""Validateurs des mots de passe (inscription, réinitialisation, back-office, Django admin).

Les 4 validateurs de Django font foi (D-79). La similarité est comparée à l'e-mail, au prénom
et au nom : le modèle a `prenom` / `nom`, pas les `first_name` / `last_name` de Django.
"""

_MODULE = "django.contrib.auth.password_validation"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": f"{_MODULE}.UserAttributeSimilarityValidator",
        "OPTIONS": {"user_attributes": ("email", "prenom", "nom")},
    },
    {"NAME": f"{_MODULE}.MinimumLengthValidator"},
    {"NAME": f"{_MODULE}.CommonPasswordValidator"},
    {"NAME": f"{_MODULE}.NumericPasswordValidator"},
]
