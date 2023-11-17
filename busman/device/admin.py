from django.contrib import admin
from django.db import models
from django.forms import Textarea, TextInput

from device.models import Device, Route


class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "mac", "ip")
    search_fields = ("name", "mac", "ip")
    ordering = ("name",)


class RouteAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "sink")
    search_fields = ("id", "source", "sink")
    ordering = ("id",)

    formfield_overrides = {
        models.TextField: {"widget": TextInput(attrs={"size": "40"})},
    }


admin.site.register(Device, DeviceAdmin)
admin.site.register(Route, RouteAdmin)
