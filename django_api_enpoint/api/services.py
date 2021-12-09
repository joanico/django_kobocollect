import os
import requests
from .models import Beneficiary
from django.conf import settings

def get_apis():
    url = 'https://kobo.humanitarianresponse.info/api/v2/assets/aWN5dGyNjJSL8nZwxqh4E8/data/?format=json'
    r = requests.get(url, headers={'Authorization': settings.ACCESS_TOKEN})
    koboapi_json = r.json()
    koboapi_list = []
    for i in range(len(koboapi_json['results'])):
        koboapi_list.append(koboapi_json['results'][i])
    return koboapi_list

def store_api():
    results = get_apis()
    for i in results:
        beneficiary_data = Beneficiary(
            name = i['Naran'],
            date = i['Data'],
            municipality = i['Municipiu'],
            postadmin = i['Postu'],
            suco = i['Suco'],
        )
        beneficiary_data.save()
    return beneficiary_data
    
