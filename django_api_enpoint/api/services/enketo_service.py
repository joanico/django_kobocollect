"""
Enketo Express integration service.

This service handles communication with the Enketo Express API for form rendering
and submission retrieval.
"""
import logging
import requests
import base64
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any
from django.conf import settings

from ..exceptions import (
    EnketoConnectionError,
    EnketoFormRenderError,
    EnketoSubmissionError,
    EnketoConfigurationError,
)

logger = logging.getLogger(__name__)


class EnketoService:
    """
    Service for interacting with Enketo Express API.
    
    Handles form rendering and submission retrieval operations.
    """
    
    def __init__(self, check_connection=False):
        """
        Initialize Enketo service with configuration from settings.
        
        Args:
            check_connection: If True, verify connection to Enketo on initialization
        """
        self.enketo_url = getattr(settings, 'ENKETO_URL', None)
        self.api_token = getattr(settings, 'ENKETO_API_TOKEN', None)
        self.timeout = getattr(settings, 'ENKETO_REQUEST_TIMEOUT', 30)
        self.enabled = bool(self.enketo_url)
        
        if not self.enketo_url:
            logger.warning(
                'ENKETO_URL is not configured. Enketo integration is disabled. '
                'Set ENKETO_URL environment variable to enable Enketo integration.'
            )
            return
        
        if not self.api_token:
            logger.warning(
                'ENKETO_API_TOKEN is not configured. Some operations may fail. '
                'Set ENKETO_API_TOKEN environment variable for authentication.'
            )
        
        # Normalize URL (remove trailing slash)
        if self.enketo_url:
            self.enketo_url = self.enketo_url.rstrip('/')
        
        # Check connection if requested
        if check_connection and self.enabled:
            try:
                self.check_connection()
            except EnketoConnectionError:
                logger.warning('Enketo service is not available. Form rendering will fail.')
    
    def check_connection(self) -> bool:
        """
        Check if Enketo service is available.
        
        Returns:
            True if connection is successful
            
        Raises:
            EnketoConnectionError: If connection fails
            EnketoConfigurationError: If not configured
        """
        if not self.enabled:
            raise EnketoConfigurationError(
                'Enketo is not configured. Please set ENKETO_URL environment variable.'
            )
        
        try:
            # Try a simple GET request to check connectivity
            response = requests.get(
                f"{self.enketo_url}/",
                headers=self._get_headers(),
                timeout=5
            )
            return True
        except requests.exceptions.ConnectionError as e:
            raise EnketoConnectionError(
                f"Unable to connect to Enketo service at {self.enketo_url}. "
                f"Please ensure Enketo is running and accessible. Error: {str(e)}"
            )
        except requests.exceptions.Timeout:
            raise EnketoConnectionError(
                f"Connection to Enketo service at {self.enketo_url} timed out."
            )
        except Exception as e:
            raise EnketoConnectionError(
                f"Error checking Enketo connection: {str(e)}"
            )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get default headers for Enketo API requests."""
        headers = {
            'Content-Type': 'application/json',
        }
        if self.api_token:
            # Enketo Express uses Basic Auth with API key as username
            # Format: Basic base64(api_key:password)
            # Password can be empty, but Basic Auth requires the colon
            credentials = f"{self.api_token}:"
            encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            headers['Authorization'] = f'Basic {encoded_credentials}'
        return headers
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        retries: int = 2
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Enketo API with error handling and retries.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request payload (for POST/PUT requests)
            retries: Number of retry attempts
            
        Returns:
            Response JSON data
            
        Raises:
            EnketoConnectionError: If connection fails
            EnketoServiceException: For other API errors
        """
        url = f"{self.enketo_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        for attempt in range(retries + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=self._get_headers(),
                    timeout=self.timeout
                )
                
                # Log request for debugging
                logger.debug(
                    f"Enketo API {method} {url} - Status: {response.status_code}"
                )
                
                # Handle successful response
                if response.status_code in (200, 201):
                    try:
                        return response.json()
                    except ValueError:
                        return {'success': True, 'data': response.text}
                
                # Handle client errors (4xx)
                if 400 <= response.status_code < 500:
                    error_msg = f"Client error: {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('message', error_data.get('detail', error_msg))
                    except ValueError:
                        error_msg = response.text or error_msg
                    
                    logger.error(f"Enketo API error: {error_msg}")
                    raise EnketoFormRenderError(error_msg)
                
                # Handle server errors (5xx) - retry
                if response.status_code >= 500:
                    if attempt < retries:
                        logger.warning(
                            f"Enketo API server error {response.status_code}, "
                            f"retrying ({attempt + 1}/{retries})..."
                        )
                        continue
                    else:
                        error_msg = f"Server error: {response.status_code}"
                        logger.error(f"Enketo API error after retries: {error_msg}")
                        raise EnketoConnectionError(error_msg)
                
            except requests.exceptions.Timeout:
                if attempt < retries:
                    logger.warning(
                        f"Enketo API timeout, retrying ({attempt + 1}/{retries})..."
                    )
                    continue
                else:
                    logger.error("Enketo API request timed out")
                    raise EnketoConnectionError("Request to Enketo service timed out")
            
            except requests.exceptions.ConnectionError as e:
                if attempt < retries:
                    logger.warning(
                        f"Enketo API connection error, retrying ({attempt + 1}/{retries})..."
                    )
                    continue
                else:
                    error_msg = (
                        f"Unable to connect to Enketo service at {self.enketo_url}. "
                        f"Please ensure:\n"
                        f"1. Enketo Express is running (check: {self.enketo_url})\n"
                        f"2. ENKETO_URL is correctly set in your environment\n"
                        f"3. Network connectivity is available\n"
                        f"Error details: {str(e)}"
                    )
                    logger.error(error_msg)
                    raise EnketoConnectionError(error_msg)
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Enketo API request error: {str(e)}")
                raise EnketoConnectionError(f"Request failed: {str(e)}")
        
        # Should not reach here, but just in case
        raise EnketoConnectionError("Failed to complete request after retries")
    
    def render_form(
        self,
        form_xml: str,
        instance_id: Optional[str] = None,
        return_url: Optional[str] = None,
        form_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Render a form using Enketo Express.
        
        Args:
            form_xml: XForm XML content
            instance_id: Optional instance ID for editing existing submissions
            return_url: Optional return URL after form submission
            
        Returns:
            Dictionary containing form rendering response with 'url' and 'offline_url' keys
            
        Raises:
            EnketoFormRenderError: If form rendering fails
            EnketoConnectionError: If connection to Enketo fails
            EnketoConfigurationError: If Enketo is not configured
        """
        if not self.enabled:
            raise EnketoConfigurationError(
                'Enketo is not configured. Please set ENKETO_URL environment variable. '
                'Example: export ENKETO_URL=http://localhost:8005'
            )
        
        if not form_xml:
            raise EnketoFormRenderError("Form XML content is required")
        
        # Use provided form_id, or extract from XML, or generate one
        form_id_from_xml = form_id
        if not form_id_from_xml:
            # Extract form_id from XML (required by Enketo Express)
            # The form_id is typically in the root instance element's id attribute
            try:
                root = ET.fromstring(form_xml)
                # Look for instance element and get its id attribute
                # XPath: //instance/*[@id] or //instance/* (first child element name)
                for instance in root.findall('.//{http://www.w3.org/2002/xforms}instance'):
                    if instance is not None and len(instance) > 0:
                        first_child = instance[0]
                        # Try id attribute first
                        form_id_from_xml = first_child.get('id')
                        if not form_id_from_xml:
                            # Fallback to element tag name
                            form_id_from_xml = first_child.tag
                            # Remove namespace if present
                            if '}' in form_id_from_xml:
                                form_id_from_xml = form_id_from_xml.split('}')[-1]
                        break
            except ET.ParseError:
                logger.warning("Could not parse XML to extract form_id, will use generated ID")
            
            # If we couldn't extract from XML, generate a form_id based on XML hash
            if not form_id_from_xml:
                import hashlib
                form_id_from_xml = hashlib.md5(form_xml.encode('utf-8')).hexdigest()[:16]
                logger.info(f"Generated form_id from XML hash: {form_id_from_xml}")
        
        # Build server URL (where form submissions will be sent)
        # Enketo Express requires this to know where to send form submissions
        server_url = getattr(settings, 'SITE_URL', '').strip()
        if not server_url:
            # Fallback: use localhost:8000 (Django server)
            server_url = 'http://localhost:8000'
        else:
            server_url = server_url.rstrip('/')
        
        # Build return URL if not provided
        if not return_url:
            try:
                return_url = f"{settings.SITE_URL}/api/forms/submit/"
            except AttributeError:
                # Fallback if SITE_URL is not configured
                return_url = None
        
        payload = {
            'form': form_xml,
            'server_url': server_url,  # Required by Enketo Express
            'form_id': form_id_from_xml,  # Required by Enketo Express
        }
        
        if instance_id:
            payload['instance_id'] = instance_id
        
        if return_url:
            payload['return_url'] = return_url
        
        logger.info(f"Rendering form in Enketo (instance_id: {instance_id})")
        
        try:
            response = self._make_request('POST', '/api/v2/survey', data=payload)
            logger.info("Form rendered successfully in Enketo")
            return response
        except EnketoConnectionError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error rendering form: {str(e)}")
            raise EnketoFormRenderError(f"Failed to render form: {str(e)}")
    
    def get_submission(self, submission_id: str) -> Dict[str, Any]:
        """
        Retrieve submission data from Enketo.
        
        Args:
            submission_id: Enketo submission ID
            
        Returns:
            Dictionary containing submission data
            
        Raises:
            EnketoSubmissionError: If submission retrieval fails
            EnketoConnectionError: If connection to Enketo fails
        """
        if not submission_id:
            raise EnketoSubmissionError("Submission ID is required")
        
        logger.info(f"Retrieving submission {submission_id} from Enketo")
        
        try:
            response = self._make_request('GET', f'/api/v2/survey/{submission_id}')
            logger.info(f"Submission {submission_id} retrieved successfully")
            return response
        except EnketoConnectionError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving submission: {str(e)}")
            raise EnketoSubmissionError(f"Failed to retrieve submission: {str(e)}")

