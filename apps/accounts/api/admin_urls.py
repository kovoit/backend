from django.urls import path

from apps.accounts.api import admin_views as views

urlpatterns = [
    path("utilisateurs/", views.UtilisateurListeVue.as_view(), name="admin-utilisateurs"),
    path(
        "utilisateurs/<uuid:pk>/",
        views.UtilisateurDetailVue.as_view(),
        name="admin-utilisateur-detail",
    ),
    path(
        "utilisateurs/<uuid:pk>/suspendre/",
        views.UtilisateurSuspendreVue.as_view(),
        name="admin-utilisateur-suspendre",
    ),
    path(
        "utilisateurs/<uuid:pk>/reactiver/",
        views.UtilisateurReactiverVue.as_view(),
        name="admin-utilisateur-reactiver",
    ),
]
