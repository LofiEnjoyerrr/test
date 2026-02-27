from django.contrib import admin

from doctors.models import Doctor, Lpu, LpuInformation, WorkPlace


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    pass


@admin.register(Lpu)
class LpuAdmin(admin.ModelAdmin):
    pass


@admin.register(LpuInformation)
class LpuInformationAdmin(admin.ModelAdmin):
    pass


@admin.register(WorkPlace)
class WorkPlaceAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'lpu')
