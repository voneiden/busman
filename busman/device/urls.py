from django.urls import path
from . import views

urlpatterns = [
    path("v1/routes/", views.RouteView.as_view({"get": "list"}), name="routes"),
    path("v1/ubootp/<str:mac>/", views.Ubootp.as_view(), name="ubootp"),
]
