"""
Django management command to list Kobo Toolbox assets and their IDs.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import requests


class Command(BaseCommand):
    help = 'List all Kobo Toolbox assets (forms) and their Asset IDs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--api-url',
            type=str,
            default=getattr(settings, 'KOBO_API_BASE_URL', 'https://kf.kobotoolbox.org/api/v2'),
            help='Kobo API base URL'
        )
        parser.add_argument(
            '--token',
            type=str,
            default=getattr(settings, 'ACCESS_TOKEN', None),
            help='Kobo API access token (or set ACCESS_TOKEN in .env)'
        )

    def handle(self, *args, **options):
        api_url = options['api_url']
        access_token = options['token']
        
        if not access_token:
            self.stdout.write(
                self.style.ERROR(
                    'ACCESS_TOKEN is not set. Please set it in your .env file or use --token option.'
                )
            )
            return
        
        headers = {
            'Authorization': f'Token {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            self.stdout.write(self.style.SUCCESS('Fetching assets from Kobo API...'))
            response = requests.get(f'{api_url}/assets/', headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            assets = data.get('results', [])
            
            if not assets:
                self.stdout.write(self.style.WARNING('No assets found.'))
                return
            
            self.stdout.write(self.style.SUCCESS(f'\nFound {len(assets)} asset(s):\n'))
            
            for i, asset in enumerate(assets, 1):
                asset_id = asset.get('uid', 'N/A')
                name = asset.get('name', 'Unnamed')
                date_created = asset.get('date_created', 'N/A')
                date_modified = asset.get('date_modified', 'N/A')
                
                self.stdout.write(f"{i}. {self.style.SUCCESS(name)}")
                self.stdout.write(f"   Asset ID: {self.style.WARNING(asset_id)}")
                self.stdout.write(f"   Created: {date_created}")
                self.stdout.write(f"   Modified: {date_modified}")
                self.stdout.write(f"   URL: {api_url}/assets/{asset_id}/")
                self.stdout.write('')
            
            self.stdout.write(self.style.SUCCESS('\nTo use an asset, add this to your .env file:'))
            self.stdout.write(f'KOBO_DEFAULT_ASSET_ID={assets[0].get("uid")}')
            
        except requests.exceptions.RequestException as e:
            self.stdout.write(
                self.style.ERROR(f'Error fetching assets: {str(e)}')
            )
            self.stdout.write(
                self.style.WARNING(
                    '\nMake sure:\n'
                    '1. ACCESS_TOKEN is correct\n'
                    '2. You have internet connection\n'
                    '3. The API URL is correct'
                )
            )
