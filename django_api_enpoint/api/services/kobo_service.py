"""
Kobo API integration service.

This service handles communication with the Kobo Toolbox API for fetching
and storing form data.
"""
import logging
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from ..models import Beneficiary, FormDefinition, FormSubmission

logger = logging.getLogger(__name__)


class KoboService:
    """
    Service for interacting with Kobo Toolbox API.
    
    Handles fetching form data and storing it in the database.
    """
    
    def __init__(self):
        """Initialize Kobo service with configuration from settings."""
        self.access_token = getattr(settings, 'ACCESS_TOKEN', None)
        self.api_base_url = getattr(settings, 'KOBO_API_BASE_URL', 'https://kf.kobotoolbox.org/api/v2')
        self.timeout = getattr(settings, 'KOBO_REQUEST_TIMEOUT', 30)
        
        if not self.access_token:
            logger.warning('ACCESS_TOKEN is not configured. Kobo API operations may fail.')
    
    def _get_headers(self) -> Dict[str, str]:
        """Get default headers for Kobo API requests."""
        headers = {
            'Content-Type': 'application/json',
        }
        if self.access_token:
            # Kobo API v2 uses Token authentication
            # Support both "Token {token}" format and plain token
            if self.access_token.startswith('Token '):
                headers['Authorization'] = self.access_token
            else:
                headers['Authorization'] = f'Token {self.access_token}'
        return headers
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Kobo API with error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Response JSON data
            
        Raises:
            requests.RequestException: If request fails
        """
        url = f"{self.api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            logger.debug(
                f"Kobo API {method} {url} - Status: {response.status_code}"
            )
            
            return response.json()
        
        except requests.exceptions.Timeout:
            logger.error("Kobo API request timed out")
            raise
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Kobo API connection error: {str(e)}")
            raise
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"Kobo API HTTP error: {str(e)}")
            raise
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Kobo API request error: {str(e)}")
            raise
    
    def get_apis(self, asset_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch form data from Kobo API.
        
        Args:
            asset_id: Optional Kobo asset ID. If not provided, uses default from settings.
            
        Returns:
            Dictionary containing Kobo API response with form data
            
        Raises:
            requests.RequestException: If API request fails
        """
        if not asset_id:
            # Default asset ID - can be overridden via settings
            asset_id = getattr(settings, 'KOBO_DEFAULT_ASSET_ID', 'aWN5dGyNjJSL8nZwxqh4E8')
        
        endpoint = f'assets/{asset_id}/data/'
        params = {'format': 'json'}
        
        logger.info(f"Fetching data from Kobo API for asset: {asset_id}")
        
        try:
            data = self._make_request('GET', endpoint, params=params)
            logger.info(f"Successfully fetched {len(data.get('results', []))} records from Kobo")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch data from Kobo API: {str(e)}")
            raise
    
    def store_api(self, asset_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch and store Kobo form data in the database.
        
        Args:
            asset_id: Optional Kobo asset ID. If not provided, uses default from settings.
            
        Returns:
            Dictionary containing information about stored records
            
        Raises:
            requests.RequestException: If API request fails
        """
        try:
            koboapi_json = self.get_apis(asset_id)
            results = koboapi_json.get('results', [])
            
            stored_count = 0
            errors = []
            
            for record in results:
                try:
                    beneficiary_data = Beneficiary(
                        name=record.get('Naran'),
                        date=record.get('Data'),
                        municipality=record.get('Municipiu'),
                        postadmin=record.get('Postu'),
                        suco=record.get('Suco'),
                    )
                    beneficiary_data.save()
                    stored_count += 1
                except Exception as e:
                    error_msg = f"Failed to store record: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            logger.info(f"Stored {stored_count} records from Kobo API")
            
            return {
                'stored_count': stored_count,
                'total_records': len(results),
                'errors': errors,
                'last_record': results[-1] if results else None
            }
        
        except Exception as e:
            logger.error(f"Failed to store Kobo API data: {str(e)}")
            raise
    
    def list_forms(self) -> List[Dict[str, Any]]:
        """
        Fetch list of all forms (assets) from Kobo API.
        
        Returns:
            List of form dictionaries with asset information
            
        Raises:
            requests.RequestException: If API request fails
        """
        endpoint = 'assets/'
        params = {'format': 'json'}
        
        logger.info("Fetching forms list from Kobo API")
        
        try:
            data = self._make_request('GET', endpoint, params=params)
            forms = data.get('results', [])
            logger.info(f"Successfully fetched {len(forms)} forms from Kobo")
            return forms
        except Exception as e:
            logger.error(f"Failed to fetch forms from Kobo API: {str(e)}")
            raise
    
    def get_form_details(self, asset_id: str) -> Dict[str, Any]:
        """
        Fetch detailed information about a specific form (asset) from Kobo API.
        
        Args:
            asset_id: Kobo asset ID
            
        Returns:
            Dictionary containing form details including XML content
            
        Raises:
            requests.RequestException: If API request fails
        """
        endpoint = f'assets/{asset_id}/'
        params = {'format': 'json'}
        
        logger.info(f"Fetching form details from Kobo API for asset: {asset_id}")
        
        try:
            data = self._make_request('GET', endpoint, params=params)
            logger.info(f"Successfully fetched form details for asset: {asset_id}")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch form details from Kobo API: {str(e)}")
            raise
    
    def get_form_xml(self, asset_id: str) -> str:
        """
        Fetch the XForm XML content for a specific form.
        
        Args:
            asset_id: Kobo asset ID
            
        Returns:
            XForm XML content as string
            
        Raises:
            requests.RequestException: If API request fails
        """
        form_details = self.get_form_details(asset_id)
        
        # Kobo API v2 stores XML in different possible locations
        # Try 'content' field first (most common - it's a string containing the XML)
        if 'content' in form_details and form_details['content']:
            content = form_details['content']
            if isinstance(content, str):
                # Check if it's already XML
                if content.strip().startswith('<?xml') or content.strip().startswith('<'):
                    return content
            elif isinstance(content, dict):
                if 'xml' in content:
                    return content['xml']
                elif 'content' in content:
                    return content['content']
        
        # Try 'xform' field
        if 'xform' in form_details and form_details['xform']:
            xform = form_details['xform']
            if isinstance(xform, str):
                return xform
            elif isinstance(xform, dict) and 'xml' in xform:
                return xform['xml']
        
        # Try fetching XML directly from form endpoint (different API structure)
        try:
            # Some Kobo instances use this endpoint
            endpoint = f'assets/{asset_id}/form.json'
            xml_response = self._make_request('GET', endpoint)
            if isinstance(xml_response, str):
                return xml_response
            elif isinstance(xml_response, dict):
                if 'xml' in xml_response:
                    return xml_response['xml']
                elif 'content' in xml_response:
                    return xml_response['content']
        except Exception as e:
            logger.debug(f"Could not fetch XML from form endpoint: {str(e)}")
        
        # Try to get from asset snapshot (deployed version)
        try:
            if 'deployed_versions' in form_details and form_details['deployed_versions']:
                # Get the latest deployed version
                latest_version = form_details['deployed_versions'][-1]
                if isinstance(latest_version, dict) and 'content' in latest_version:
                    return latest_version['content']
        except Exception as e:
            logger.debug(f"Could not fetch XML from deployed version: {str(e)}")
        
        raise ValueError(f"Could not find XML content in form details for asset: {asset_id}. Available fields: {list(form_details.keys())}")
    
    def import_form(self, asset_id: str, overwrite: bool = False) -> Dict[str, Any]:
        """
        Import a form from Kobo into Django FormDefinition model.
        
        Args:
            asset_id: Kobo asset ID
            overwrite: If True, update existing form if it already exists
            
        Returns:
            Dictionary with import results
            
        Raises:
            requests.RequestException: If API request fails
        """
        try:
            form_details = self.get_form_details(asset_id)
            form_xml = self.get_form_xml(asset_id)
            
            # Extract form name and ID
            form_name = form_details.get('name', f'Form {asset_id}')
            kobo_id = asset_id
            
            # Try to extract form ID from XML
            xml_form_id = None
            try:
                root = ET.fromstring(form_xml)
                for instance in root.findall('.//{http://www.w3.org/2002/xforms}instance'):
                    if len(instance) > 0:
                        first = instance[0]
                        xml_form_id = first.get('id')
                        if not xml_form_id:
                            xml_form_id = first.tag
                            if '}' in xml_form_id:
                                xml_form_id = xml_form_id.split('}')[-1]
                        break
            except ET.ParseError:
                logger.warning(f"Could not parse XML to extract form ID for asset: {asset_id}")
            
            # Get version from form details or default to 1.0
            version = form_details.get('version_id', '1.0')
            
            # Check if form already exists
            form, created = FormDefinition.objects.get_or_create(
                kobo_id=kobo_id,
                defaults={
                    'name': form_name,
                    'xml_content': form_xml,
                    'version': version,
                }
            )
            
            if not created and overwrite:
                # Update existing form
                form.name = form_name
                form.xml_content = form_xml
                form.version = version
                form.save()
                action = 'updated'
            elif not created:
                action = 'exists'
            else:
                action = 'created'
            
            logger.info(f"Form import {action}: {form_name} (Kobo ID: {kobo_id})")
            
            return {
                'success': True,
                'action': action,
                'form_id': form.id,
                'form_name': form_name,
                'kobo_id': kobo_id,
                'xml_form_id': xml_form_id,
                'version': version,
            }
            
        except Exception as e:
            logger.error(f"Failed to import form from Kobo: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'asset_id': asset_id,
            }
    
    def get_submissions(self, asset_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch submissions for a specific form from Kobo API.
        
        Args:
            asset_id: Kobo asset ID
            limit: Optional limit on number of submissions to fetch
            
        Returns:
            List of submission dictionaries
            
        Raises:
            requests.RequestException: If API request fails
        """
        endpoint = f'assets/{asset_id}/data/'
        params = {'format': 'json'}
        if limit:
            params['limit'] = limit
        
        logger.info(f"Fetching submissions from Kobo API for asset: {asset_id}")
        
        try:
            data = self._make_request('GET', endpoint, params=params)
            submissions = data.get('results', [])
            logger.info(f"Successfully fetched {len(submissions)} submissions from Kobo")
            return submissions
        except Exception as e:
            logger.error(f"Failed to fetch submissions from Kobo API: {str(e)}")
            raise
    
    def import_submissions(
        self,
        asset_id: str,
        form: Optional[FormDefinition] = None,
        limit: Optional[int] = None,
        user=None
    ) -> Dict[str, Any]:
        """
        Import submissions from Kobo into Django FormSubmission model.
        
        Args:
            asset_id: Kobo asset ID
            form: Optional FormDefinition instance. If not provided, will try to find by kobo_id
            limit: Optional limit on number of submissions to import
            user: Optional user to associate with submissions
            
        Returns:
            Dictionary with import results
            
        Raises:
            requests.RequestException: If API request fails
        """
        try:
            # Get or find form
            if not form:
                try:
                    form = FormDefinition.objects.get(kobo_id=asset_id)
                except FormDefinition.DoesNotExist:
                    return {
                        'success': False,
                        'error': f'Form with Kobo ID {asset_id} not found. Import the form first.',
                        'asset_id': asset_id,
                    }
            
            # Fetch submissions
            submissions_data = self.get_submissions(asset_id, limit=limit)
            
            imported_count = 0
            skipped_count = 0
            errors = []
            
            for submission_data in submissions_data:
                try:
                    # Extract submission ID (usually _id or id field)
                    submission_id = submission_data.get('_id') or submission_data.get('id')
                    
                    # Check if submission already exists (by submission ID in JSON)
                    existing = FormSubmission.objects.filter(
                        form=form,
                        submission_data__contains={'_id': submission_id}
                    ).first()
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Create new submission
                    submission = FormSubmission(
                        form=form,
                        user=user,
                        submission_data=submission_data,
                        status='submitted'
                    )
                    submission.save()
                    imported_count += 1
                    
                except Exception as e:
                    error_msg = f"Failed to import submission: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            logger.info(
                f"Imported {imported_count} submissions for form {form.name} "
                f"(skipped {skipped_count} existing)"
            )
            
            return {
                'success': True,
                'imported_count': imported_count,
                'skipped_count': skipped_count,
                'total_submissions': len(submissions_data),
                'errors': errors,
                'form_id': form.id,
                'form_name': form.name,
            }
            
        except Exception as e:
            logger.error(f"Failed to import submissions from Kobo: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'asset_id': asset_id,
            }

