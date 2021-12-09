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

class ApiView(TemplateView):
    template_name =  'api/api_endpoint.html'
    def get_context_data(self, *args, **kwargs):
        context = super(ApiView, self).get_context_data(*args, **kwargs)
        context['all_beneficiary'] = Beneficiary.objects.all().order_by('-id')
        return context

class GetKoboApi(TemplateView):
    template_name = 'api/kobo_list.html'
    def get_context_data(self, *args, **kwargs):
        context = {
            'koboapi' : get_apis(),
        }
        return context

