from django.urls import path

from apps.portefeuille.api import admin_views as views

urlpatterns = [
    path("transactions/", views.TransactionAdminListeVue.as_view(), name="admin-transactions"),
    path(
        "transactions/<uuid:pk>/verser/",
        views.RetraitVerserVue.as_view(),
        name="admin-retrait-verser",
    ),
    path(
        "transactions/<uuid:pk>/refuser/",
        views.RetraitRefuserVue.as_view(),
        name="admin-retrait-refuser",
    ),
]
