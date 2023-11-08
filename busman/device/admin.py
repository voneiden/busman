from django.contrib import admin

from device.models import Device


# Register your models here.
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "mac", "ip")
    search_fields = ("name", "mac", "ip")
    ordering = ("name",)


admin.site.register(Device, DeviceAdmin)
