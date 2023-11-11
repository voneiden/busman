from django.urls import path
from . import views

urlpatterns = [
    path("v1/ubootp/<str:mac>/", views.Ubootp.as_view(), name="ubootp"),
]
