import os
import requests
from .models import Beneficiary
from django.conf import settings

def get_apis():
    # get kobo api
    url = 'https://kobo.humanitarianresponse.info/api/v2/assets/aWN5dGyNjJSL8nZwxqh4E8/data/?format=json'
    r = requests.get(url, headers={'Authorization': settings.ACCESS_TOKEN}) # kobo access token allow to access kobo data
    koboapi_json = r.json() # return to json format
    return koboapi_json

def store_api():
    koboapi_json = get_apis()
    for i in koboapi_json['results']:
        beneficiary_data = Beneficiary(
            name = i['Naran'],
            date = i['Data'],
            municipality = i['Municipiu'],
            postadmin = i['Postu'],
            suco = i['Suco'],
        )
        beneficiary_data.save()
    return i
    
