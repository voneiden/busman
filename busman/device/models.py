from django.db.models import Model, TextField
from netfields import InetAddressField, MACAddressField


class Device(Model):
    name = TextField(null=False, blank=False, unique=True)
    mac = MACAddressField(unique=True)
    ip = InetAddressField(unique=True)


class Route(Model):
    source = TextField(null=False, blank=False)
    sink = TextField(null=False, blank=False)

    class Meta:
        unique_together = (("source", "sink"),)

    def __str__(self):
        return f"Route: [{self.source}] → [{self.sink}]"
