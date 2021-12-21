from django.core.management.base import BaseCommand, CommandError
from api.services import get_apis, store_api
from api.models import Beneficiary

class Command(BaseCommand):
    help = 'Displays current time'

    def handle(self, *args, **kwargs):

        # Show this if the data already exist in the database
        if Beneficiary.objects.exists():
            print('Beneficiary data already loaded...exiting.')
            return

            # Show this before loading the data into the database
            print("Loading childrens data")
        else:
            return store_api()



