from django.shortcuts import render
from django.views.generic import TemplateView
from .services import get_koboapi
from ast import literal_eval
from .models import Beneficiary, Municipality, PostAdmin, Suco
import requests

def api(request):
    response=requests.get('https://localcoviddata.com/covid19/v1/cases/jhu?state=CA&daysInPast=7').json()
    return render(request, 'api/api_endpoint.html',{'response':response})

class GetKoboApi(TemplateView):
    template_name = 'api/kobo_list.html'
    def get_context_data(self, *args, **kwargs):
        context = {
            'koboapi' : get_koboapi(),
        }
        context['municipalities'] = Municipality.objects.all()
        return context
