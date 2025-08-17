from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Command to print a text"
    def handle(self, *args, **options):
            try:
                print('Command is executed')
            except Exception as e:
                raise CommandError(e)
