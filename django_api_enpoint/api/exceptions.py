"""
Custom exceptions for Enketo integration.
"""
from rest_framework.exceptions import APIException
from rest_framework import status


class EnketoServiceException(APIException):
    """Base exception for Enketo service errors."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'An error occurred with the Enketo service.'
    default_code = 'enketo_service_error'


class EnketoConnectionError(EnketoServiceException):
    """Raised when unable to connect to Enketo service."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Unable to connect to Enketo service.'
    default_code = 'enketo_connection_error'


class EnketoFormRenderError(EnketoServiceException):
    """Raised when form rendering fails."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Failed to render form in Enketo.'
    default_code = 'enketo_form_render_error'


class EnketoSubmissionError(EnketoServiceException):
    """Raised when form submission fails."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Failed to process form submission.'
    default_code = 'enketo_submission_error'


class EnketoConfigurationError(EnketoServiceException):
    """Raised when Enketo configuration is invalid."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'Enketo service is not properly configured.'
    default_code = 'enketo_configuration_error'

