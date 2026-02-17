"""
Custom permission classes for API endpoints.
"""
from rest_framework import permissions


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Custom permission that allows read-only access to unauthenticated users,
    but requires authentication for write operations.
    """
    
    def has_permission(self, request, view):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions require authentication
        return request.user and request.user.is_authenticated


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission that allows read-only access to all users,
    but only allows owners to modify their own submissions.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the submission
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # For other objects, require authentication
        return request.user and request.user.is_authenticated


class IsFormOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission for form-related operations.
    Allows read access to all users (authenticated and unauthenticated),
    but requires authentication for write operations.
    """
    
    def has_permission(self, request, view):
        # Read permissions are allowed for any request (including unauthenticated)
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions require authentication
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions require authentication
        # Can be extended to check ownership if needed
        return request.user and request.user.is_authenticated

