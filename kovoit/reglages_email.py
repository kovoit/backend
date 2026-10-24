"""Email et liens envoyés par email (importé par settings.py). Variables lues dans l'environnement
(le fichier .env est déjà chargé par settings.py)."""

import environ

env = environ.Env()

# Email (Gmail SMTP en production, console en développement)
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Kovoit <no-reply@kovoittg.com>")
EMAIL_TIMEOUT = 10

# Back-office : adresse utilisée dans le lien « réinitialiser mon mot de passe »
BACKOFFICE_URL = env("BACKOFFICE_URL", default="http://localhost:5173")
# Durée de validité de ce lien (secondes) : 1 h
PASSWORD_RESET_TIMEOUT = 60 * 60
