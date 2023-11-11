from netfields.rest_framework import MACAddressField
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.fields import CharField
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from device.models import Device


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
