import os
import requests

# get kobo api endpoint
def get_koboapi():
    url = 'https://kobo.humanitarianresponse.info/api/v2/assets/aWN5dGyNjJSL8nZwxqh4E8/data/?format=json'
    r = requests.get(url, headers={'Authorization': 'Token 7e6536da41513caf05449d19127762748b88b748'})
    koboapi_json = r.json()
    koboapi_list = []
    for i in range(len(koboapi_json['results'])):
        koboapi_list.append(koboapi_json['results'][i])
    return koboapi_list
