from django.contrib import admin
from .models import Beneficiary, Municipality, PostAdmin, Suco

@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = ['bene_id', 'date', 'name', 'municipality', 'postadmin', 'suco']
    list_filter = ['name']

@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(PostAdmin)
class PostAdmin(admin.ModelAdmin):
    list_display = ['name', 'municipality']

@admin.register(Suco)
class SucoAdmin(admin.ModelAdmin):
    list_display = ['name', 'postadmin']
