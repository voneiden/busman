from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Model, TextField, IntegerField, ManyToManyField
from netfields import InetAddressField, MACAddressField


class Device(Model):
    name = TextField(null=False, blank=False, unique=True)
    mac = MACAddressField(unique=True)
    ip = InetAddressField(unique=True)

    twi_modules = ManyToManyField("TWIModule", blank=True)

    def __str__(self):
        return f"Device: {self.name}"


class TWIModule(Model):
    name = TextField(null=False, blank=False, unique=True)
    address = IntegerField(
        validators=[MaxValueValidator(127), MinValueValidator(1)]
    )

    def __str__(self):
        return f"TWIModule: {self.name} ({self.address})"


class Route(Model):
    source = TextField(null=False, blank=False)
    sink = TextField(null=False, blank=False)

    class Meta:
        unique_together = (("source", "sink"),)

    def __str__(self):
        return f"Route: [{self.source}] → [{self.sink}]"
