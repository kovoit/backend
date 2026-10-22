from django.apps import AppConfig


class PortefeuilleConfig(AppConfig):
    name = "apps.portefeuille"
    label = "portefeuille"
    verbose_name = "Portefeuille"

    def ready(self):
        from apps.portefeuille.configuration import verifier_configuration_paiement

        verifier_configuration_paiement()
