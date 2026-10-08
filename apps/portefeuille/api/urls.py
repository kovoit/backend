from django.urls import path

from apps.portefeuille.api import views

urlpatterns = [
    path("portefeuille/", views.PortefeuilleVue.as_view(), name="portefeuille"),
    path(
        "portefeuille/transactions/",
        views.TransactionsVue.as_view(),
        name="portefeuille-transactions",
    ),
    path("portefeuille/recharger/", views.RechargerVue.as_view(), name="portefeuille-recharger"),
    path("portefeuille/retirer/", views.RetirerVue.as_view(), name="portefeuille-retirer"),
]
