from django.contrib import admin
from django.db import models
from django.forms import Textarea, TextInput
from django.utils.html import format_html

from device.models import Device, Route


class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "mac", "ip")
    search_fields = ("name", "mac", "ip")
    ordering = ("name",)


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


admin.site.register(Device, DeviceAdmin)
admin.site.register(Route, RouteAdmin)
