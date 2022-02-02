from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import TemplateView
from ast import literal_eval
from .models import Beneficiary
from .services import get_apis, store_api
from django.conf import settings
import requests
import coreapi
import io

def GetKoboApi(request):
    aplikante = Beneficiary.objects.all().order_by('date')
    context = {
        'aplikante': aplikante
    }
    return render(request, "api/kobo_list.html", context)
