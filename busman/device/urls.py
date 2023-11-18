from django.urls import path
from . import views

urlpatterns = [
    path(
        "routes/bulk_edit/",
        views.bulk_edit_routes_view,
        name="bulk_edit_routes",
    ),
    path("v1/routes/", views.RouteView.as_view({"get": "list"}), name="routes"),
    path("v1/ubootp/<str:mac>/", views.Ubootp.as_view(), name="ubootp"),
]
