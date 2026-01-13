from django.core.management.base import BaseCommand, CommandError
from api.services import get_apis, store_api
from api.models import Beneficiary

class Command(BaseCommand):
    help = 'Displays current time'

    def handle(self, *args, **kwargs):

        e = store_api()

        # Show this if the data already exist in the database
        if not Beneficiary.objects.filter(pk=e['_id']).exists():
            return e
            print('Succeful')
        else:
            print('Beneficiary data already loaded...exiting.')
