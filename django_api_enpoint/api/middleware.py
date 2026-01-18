"""
Middleware to disable caching for API responses.
"""
from django.utils.deprecation import MiddlewareMixin


class NoCacheAPIMiddleware(MiddlewareMixin):
    """
    Middleware to prevent browser caching of API responses.
    Adds cache-control headers to all API endpoints.
    """
    
    def process_response(self, request, response):
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response

