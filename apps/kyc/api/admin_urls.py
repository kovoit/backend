from django.urls import path

from apps.kyc.api import admin_views as views

urlpatterns = [
    path("kyc/", views.DossierListeVue.as_view(), name="admin-kyc"),
    path("kyc/<uuid:pk>/", views.DossierDetailVue.as_view(), name="admin-kyc-detail"),
    path("kyc/<uuid:pk>/valider/", views.DossierValiderVue.as_view(), name="admin-kyc-valider"),
    path("kyc/<uuid:pk>/rejeter/", views.DossierRejeterVue.as_view(), name="admin-kyc-rejeter"),
    path("kyc/pieces/<uuid:pk>/fichier/", views.PieceFichierVue.as_view(), name="admin-kyc-piece"),
]
