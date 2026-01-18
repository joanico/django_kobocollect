"""
Legacy service functions for backward compatibility.

This module provides backward-compatible function wrappers around
the new service classes. New code should use the service classes directly
from api.services.kobo_service and api.services.enketo_service.
"""
import warnings
from .services.kobo_service import KoboService
from .services.enketo_service import EnketoService

# Create service instances
_kobo_service = None
_enketo_service = None


def _get_kobo_service():
    """Get or create KoboService instance."""
    global _kobo_service
    if _kobo_service is None:
        _kobo_service = KoboService()
    return _kobo_service


def get_apis(asset_id=None):
    """
    Legacy function to get Kobo API data.
    
    DEPRECATED: Use KoboService.get_apis() instead.
    
    Args:
        asset_id: Optional Kobo asset ID
        
    Returns:
        Dictionary containing Kobo API response
    """
    warnings.warn(
        'get_apis() is deprecated. Use KoboService.get_apis() instead.',
        DeprecationWarning,
        stacklevel=2
    )
    service = _get_kobo_service()
    return service.get_apis(asset_id)


def store_api(asset_id=None):
    """
    Legacy function to fetch and store Kobo API data.
    
    DEPRECATED: Use KoboService.store_api() instead.
    
    Args:
        asset_id: Optional Kobo asset ID
        
    Returns:
        Dictionary containing information about stored records
    """
    warnings.warn(
        'store_api() is deprecated. Use KoboService.store_api() instead.',
        DeprecationWarning,
        stacklevel=2
    )
    service = _get_kobo_service()
    return service.store_api(asset_id)


# Export service classes for direct use
__all__ = ['get_apis', 'store_api', 'KoboService', 'EnketoService']
