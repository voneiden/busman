from collections import defaultdict

from django import forms
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from netfields.rest_framework import MACAddressField
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.fields import CharField
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.serializers import Serializer, ModelSerializer
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from device.models import Device, Route


class UbootRequest(Serializer):
    mac = MACAddressField()

    def validate(self, attrs):
        # attrs["device"] = get_object_or_404(Device, mac=attrs["mac"])
        # return attrs
        try:
            attrs["device"] = Device.objects.get(mac=attrs["mac"])
        except Device.DoesNotExist:
            raise ValidationError({"mac": "MAC address does not exist"}, code=404)

        return attrs


class UbootResponse(Serializer):
    ip = CharField()


class Ubootp(APIView):
    def get(self, request, *, mac):
        data = UbootRequest(data={"mac": mac})
        data.is_valid(raise_exception=True)
        return UbootResponse(data={"ip": data.validated_data["device"].ip})

        # get only ip field
        # d = get_object_or_404(Device, mac=mac)
        # return Response(data={"ip": d.ip})


class RouteSerializer(ModelSerializer):
    class Meta:
        model = Route
        fields = "__all__"


class RouteView(ListModelMixin, GenericViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer


class BulkEditRoutesForm(forms.Form):
    routes = forms.CharField(widget=forms.Textarea(attrs={"rows": "40", "cols": "100"}))


def bulk_edit_routes_view(request):
    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = BulkEditRoutesForm(request.POST)
        # check whether it's valid:
        if form.is_valid():

            def to_data(row):
                source, sink = row.split()
                return {"source": source, "sink": sink}

            routes_data = (
                to_data(row) for row in form.cleaned_data["routes"].split("\n")
            )

            Route.objects.all().delete()
            Route.objects.bulk_create(Route(**route_data) for route_data in routes_data)

            return HttpResponseRedirect(reverse_lazy("admin:device_route_changelist"))

    # if a GET (or any other method) we'll create a blank form
    else:
        routes = Route.objects.all()
        if routes.count():
            max_source_length = max(len(route.source) for route in routes)
        else:
            max_source_length = 0
        # max_sink_length = max(len(route.sink) for route in routes)

        source_col_length = max_source_length + 10
        # sink_col_length = max_sink_length + 10

        buf = (f"{route.source:<{source_col_length}} {route.sink}" for route in routes)
        form = BulkEditRoutesForm(data={"routes": "\n".join(buf)})

    return render(request, "device/bulk_edit_routes.html", {"form": form})
