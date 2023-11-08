from django.db.models import Model, TextField
from netfields import InetAddressField, MACAddressField


class Device(Model):
    name = TextField(null=False, blank=False, unique=True)
    mac = MACAddressField(unique=True)
    ip = InetAddressField(unique=True)
