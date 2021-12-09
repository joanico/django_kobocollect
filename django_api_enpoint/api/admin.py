from django.contrib import admin
from .models import Beneficiary

@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = ['date', 'name', 'municipality', 'postadmin', 'suco']
    list_filter = ['name']
