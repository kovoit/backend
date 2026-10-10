from django.urls import path

from apps.accounts.api import admin_auth_views as views

urlpatterns = [
    path("connexion/", views.ConnexionAdminVue.as_view(), name="admin-connexion"),
    path("jeton/rafraichir/", views.RafraichirAdminVue.as_view(), name="admin-jeton-rafraichir"),
    path("deconnexion/", views.DeconnexionAdminVue.as_view(), name="admin-deconnexion"),
    path("moi/", views.MoiAdminVue.as_view(), name="admin-moi"),
]
