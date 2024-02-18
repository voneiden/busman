from django.contrib import admin
from django.db import models
from django.forms import TextInput

from device.models import Device, Route, TWIModule


class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "mac", "ip")
    search_fields = ("name", "mac", "ip")
    ordering = ("name",)


admin.site.register(Device, DeviceAdmin)


class TWIModuleAdmin(admin.ModelAdmin):
    pass


admin.site.register(TWIModule, TWIModuleAdmin)


class RouteAdmin(admin.ModelAdmin):
    # save_as = True
    list_display = ("source", "sink")
    list_display_links = None
    list_editable = ("source", "sink")
    search_fields = ("source", "sink")
    ordering = ("source",)

    formfield_overrides = {
        models.TextField: {"widget": TextInput(attrs={"size": "40"})},
    }


admin.site.register(Route, RouteAdmin)
