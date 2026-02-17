"""
API views for Enketo and Kobo integration.

This module contains viewsets and views for form management,
form rendering, submission handling, and Kobo API integration.
"""
import logging
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from rest_framework import viewsets, status, generics, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.reverse import reverse

from .models import Beneficiary, FormDefinition, FormSubmission, FormMedia
from .serializers import (
    FormDefinitionSerializer,
    FormSubmissionSerializer,
    FormMediaSerializer,
    BeneficiarySerializer,
)
from .services import EnketoService, KoboService
from .permissions import IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly, IsFormOwnerOrReadOnly
from .exceptions import (
    EnketoServiceException,
    EnketoFormRenderError,
    EnketoSubmissionError,
    EnketoConnectionError,
    EnketoConfigurationError,
)

logger = logging.getLogger(__name__)


@api_view(['GET'])
def api_root(request, format=None):
    """
    API Root endpoint with clear documentation of all available endpoints.
    
    This provides a clear overview of all API endpoints and their purposes.
    """
    from django.shortcuts import render
    
    base_url = request.build_absolute_uri('/').rstrip('/')
    
    def get_url(name, pk=None):
        """Helper to get URL or return example if reverse fails."""
        try:
            if pk:
                return reverse(name, request=request, format=format, kwargs={'pk': pk})
            return reverse(name, request=request, format=format)
        except Exception:
            # If reverse fails, return example URL
            if 'form-definition' in name:
                if 'list' in name:
                    return f'{base_url}/api/forms/'
                elif 'detail' in name:
                    return f'{base_url}/api/forms/{pk}/'
                elif 'render' in name:
                    return f'{base_url}/api/forms/{pk}/render/'
                elif 'submissions' in name:
                    return f'{base_url}/api/forms/{pk}/submissions/'
            elif 'form-submission' in name:
                if 'list' in name:
                    return f'{base_url}/api/submissions/'
                elif 'detail' in name:
                    return f'{base_url}/api/submissions/{pk}/'
                elif 'submit' in name:
                    return f'{base_url}/api/submissions/submit/'
                elif 'update-status' in name:
                    return f'{base_url}/api/submissions/{pk}/update_status/'
            elif 'form-media' in name:
                if 'list' in name:
                    return f'{base_url}/api/media/'
                elif 'detail' in name:
                    return f'{base_url}/api/media/{pk}/'
            return f'{base_url}/api/'
    
    data = {
        'api_name': 'Kobo Django API',
        'version': '1.0',
        'description': 'API for managing forms, submissions, and media files',
        'endpoints': {
            'forms': {
                'list': {
                    'url': get_url('form-definition-list'),
                    'method': 'GET',
                    'description': 'List all form definitions (templates)',
                    'example': '/api/forms/'
                },
                'create': {
                    'url': get_url('form-definition-list'),
                    'method': 'POST',
                    'description': 'Create a new form definition',
                    'example': '/api/forms/'
                },
                'detail': {
                    'url': get_url('form-definition-detail', pk=1),
                    'method': 'GET',
                    'description': 'Get a specific form definition by ID',
                    'example': '/api/forms/1/'
                },
                'render': {
                    'url': get_url('form-definition-render', pk=1),
                    'method': 'POST',
                    'description': 'Render a form via Enketo Express',
                    'example': '/api/forms/1/render/'
                },
                'submissions': {
                    'url': get_url('form-definition-submissions', pk=1),
                    'method': 'GET',
                    'description': 'Get all submissions for a specific form',
                    'example': '/api/forms/1/submissions/'
                }
            },
            'submissions': {
                'list': {
                    'url': get_url('form-submission-list'),
                    'method': 'GET',
                    'description': 'List all form submissions',
                    'example': '/api/submissions/'
                },
                'create': {
                    'url': get_url('form-submission-list'),
                    'method': 'POST',
                    'description': 'Create a new form submission',
                    'example': '/api/submissions/'
                },
                'submit': {
                    'url': get_url('form-submission-submit'),
                    'method': 'POST',
                    'description': 'Submit form data (alternative endpoint)',
                    'example': '/api/submissions/submit/'
                },
                'detail': {
                    'url': get_url('form-submission-detail', pk=1),
                    'method': 'GET',
                    'description': 'Get a specific submission by ID',
                    'example': '/api/submissions/1/'
                },
                'update_status': {
                    'url': get_url('form-submission-update-status', pk=1),
                    'method': 'POST',
                    'description': 'Update the status of a submission',
                    'example': '/api/submissions/1/update_status/'
                }
            },
            'media': {
                'list': {
                    'url': get_url('form-media-list'),
                    'method': 'GET',
                    'description': 'List all media files',
                    'example': '/api/media/'
                },
                'detail': {
                    'url': get_url('form-media-detail', pk=1),
                    'method': 'GET',
                    'description': 'Get a specific media file by ID',
                    'example': '/api/media/1/'
                }
            }
        },
        'quick_links': {
            'view_all_forms': get_url('form-definition-list'),
            'view_all_submissions': get_url('form-submission-list'),
            'view_all_media': get_url('form-media-list'),
        }
    }
    
    # Get actual forms and submissions for the template
    forms = FormDefinition.objects.all().order_by('-created_at')[:10]  # Latest 10 forms
    submissions = FormSubmission.objects.all().order_by('-submitted_at')[:10]  # Latest 10 submissions
    
    # Use custom template for HTML requests, JSON for API requests
    if request.accepted_renderer.format == 'html' or 'text/html' in request.META.get('HTTP_ACCEPT', ''):
        return render(request, 'rest_framework/api_root.html', {
            'data': data,
            'endpoints': data['endpoints'],
            'quick_links': data['quick_links'],
            'forms': forms,
            'submissions': submissions,
            'forms_count': FormDefinition.objects.count(),
            'submissions_count': FormSubmission.objects.count(),
        })
    
    return Response(data)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for API responses."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def GetKoboApi(request):
    """Legacy view for rendering Kobo beneficiary list."""
    aplikante = Beneficiary.objects.all().order_by('date')
    context = {
        'aplikante': aplikante
    }
    return render(request, "api/kobo_list.html", context)


class FormDefinitionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing form definitions.
    
    Provides CRUD operations for FormDefinition model.
    """
    queryset = FormDefinition.objects.all()
    serializer_class = FormDefinitionSerializer
    permission_classes = [IsFormOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'kobo_id', 'version']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-updated_at']
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def render(self, request, pk=None):
        """
        Render a form using Enketo Express.
        
        POST /api/forms/{id}/render/
        
        Optional query parameters:
        - instance_id: ID of existing submission to edit
        - return_url: Custom return URL after submission
        """
        form = self.get_object()
        
        try:
            enketo_service = EnketoService()
            
            instance_id = request.query_params.get('instance_id')
            return_url = request.query_params.get('return_url')
            
            result = enketo_service.render_form(
                form_xml=form.xml_content,
                instance_id=instance_id,
                return_url=return_url
                # form_id will be extracted from XML automatically
            )
            
            logger.info(f"Form {form.id} rendered successfully via Enketo")
            
            return Response({
                'success': True,
                'form_id': form.id,
                'form_name': form.name,
                'enketo_url': result.get('url'),
                'enketo_offline_url': result.get('offline_url'),
                'instance_id': result.get('instance_id'),
            }, status=status.HTTP_200_OK)
        
        except EnketoFormRenderError as e:
            logger.error(f"Failed to render form {form.id}: {str(e)}")
            return Response({
                'success': False,
                'error': str(e),
                'error_code': 'form_render_error'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except EnketoServiceException as e:
            logger.error(f"Enketo service error for form {form.id}: {str(e)}")
            return Response({
                'success': False,
                'error': str(e),
                'error_code': 'enketo_service_error'
            }, status=e.status_code)
        
        except Exception as e:
            logger.error(f"Unexpected error rendering form {form.id}: {str(e)}")
            return Response({
                'success': False,
                'error': 'An unexpected error occurred',
                'error_code': 'internal_error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def submissions(self, request, pk=None):
        """
        Get all submissions for a specific form.
        
        GET /api/forms/{id}/submissions/
        """
        form = self.get_object()
        submissions = FormSubmission.objects.filter(form=form)
        
        # Apply filtering
        status_filter = request.query_params.get('status')
        if status_filter:
            submissions = submissions.filter(status=status_filter)
        
        # Paginate
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(submissions, request)
        
        if page is not None:
            serializer = FormSubmissionSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        
        serializer = FormSubmissionSerializer(submissions, many=True, context={'request': request})
        return Response(serializer.data)


class FormSubmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing form submissions.
    
    Provides CRUD operations for FormSubmission model.
    """
    queryset = FormSubmission.objects.all()
    serializer_class = FormSubmissionSerializer
    permission_classes = [IsOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['form__name', 'form__kobo_id', 'status', 'user__username']
    ordering_fields = ['submitted_at', 'status']
    ordering = ['-submitted_at']
    
    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by form
        form_id = self.request.query_params.get('form')
        if form_id:
            queryset = queryset.filter(form_id=form_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by user
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set the user to the current user when creating a submission."""
        serializer.save(user=self.request.user if self.request.user.is_authenticated else None)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def submit(self, request):
        """
        Submit a form via Enketo.
        
        POST /api/submissions/submit/
        
        Body:
        {
            "form_id": 1,
            "submission_data": {...},
            "status": "submitted"
        }
        """
        form_id = request.data.get('form_id')
        submission_data = request.data.get('submission_data')
        submission_status = request.data.get('status', 'submitted')
        
        if not form_id:
            return Response({
                'success': False,
                'error': 'form_id is required',
                'error_code': 'missing_form_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not submission_data:
            return Response({
                'success': False,
                'error': 'submission_data is required',
                'error_code': 'missing_submission_data'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            form = FormDefinition.objects.get(pk=form_id)
        except FormDefinition.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Form not found',
                'error_code': 'form_not_found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Create submission record
            submission = FormSubmission.objects.create(
                form=form,
                user=request.user if request.user.is_authenticated else None,
                submission_data=submission_data,
                status=submission_status
            )
            
            logger.info(f"Form submission {submission.id} created successfully")
            
            serializer = FormSubmissionSerializer(submission, context={'request': request})
            return Response({
                'success': True,
                'submission': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Failed to create submission: {str(e)}")
            return Response({
                'success': False,
                'error': 'Failed to create submission',
                'error_code': 'submission_creation_error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """
        Update the status of a submission.
        
        POST /api/submissions/{id}/update_status/
        
        Body:
        {
            "status": "approved" | "rejected" | "submitted"
        }
        
        Note: Uses viewset's permission_classes (IsOwnerOrReadOnly) to ensure
        only the owner can update their submission status.
        """
        submission = self.get_object()
        
        # Explicit permission check: IsOwnerOrReadOnly should handle this,
        # but we add explicit check for clarity and better error messages.
        # Staff and superusers can update any submission, regular users can only update their own.
        if not request.user.is_authenticated:
            return Response({
                'success': False,
                'error': 'Authentication required',
                'error_code': 'authentication_required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not (request.user.is_staff or request.user.is_superuser):
            if submission.user != request.user:
                return Response({
                    'success': False,
                    'error': 'You do not have permission to update this submission',
                    'error_code': 'permission_denied'
                }, status=status.HTTP_403_FORBIDDEN)
        new_status = request.data.get('status')
        
        if not new_status:
            return Response({
                'success': False,
                'error': 'status is required',
                'error_code': 'missing_status'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        valid_statuses = [choice[0] for choice in FormSubmission._meta.get_field('status').choices]
        if new_status not in valid_statuses:
            return Response({
                'success': False,
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}',
                'error_code': 'invalid_status'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        submission.status = new_status
        submission.save()
        
        serializer = FormSubmissionSerializer(submission, context={'request': request})
        return Response({
            'success': True,
            'submission': serializer.data
        }, status=status.HTTP_200_OK)


class FormMediaViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing form media files.
    
    Provides CRUD operations for FormMedia model.
    """
    queryset = FormMedia.objects.all()
    serializer_class = FormMediaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['uploaded_at']
    ordering = ['-uploaded_at']
    
    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by form
        form_id = self.request.query_params.get('form')
        if form_id:
            queryset = queryset.filter(form_id=form_id)
        
        return queryset


# ============================================================================
# Enketo Form Interface Views
# ============================================================================

def form_list_view(request):
    """
    Display a list of forms with options to fill new forms or edit existing submissions.
    
    GET /forms/
    """
    forms = FormDefinition.objects.all()
    submissions = FormSubmission.objects.all()
    
    # Group submissions by form
    form_submissions = {}
    for submission in submissions:
        form_id = submission.form.id
        if form_id not in form_submissions:
            form_submissions[form_id] = []
        form_submissions[form_id].append(submission)
    
    # Check if Enketo is available
    enketo_available = False
    enketo_status_message = None
    try:
        enketo_service = EnketoService()
        if enketo_service.enabled:
            # Enable button if Enketo is configured (even if not running)
            # The actual form rendering will handle connection errors gracefully
            enketo_available = True
            # Try to check connection (non-blocking, just for status message)
            try:
                enketo_service.check_connection()
            except EnketoConnectionError:
                enketo_status_message = (
                    "Note: Enketo Express may not be running. If you encounter errors, "
                    "please start Enketo Express on port 8005. See RUN_ENKETO_LOCALLY.md for instructions."
                )
            except Exception:
                pass  # Silently ignore other errors during status check
        else:
            enketo_status_message = (
                "Enketo Express is not configured. Set ENKETO_URL in your .env file to enable form filling."
            )
    except Exception as e:
        logger.warning(f"Could not check Enketo status: {str(e)}")
        # Still enable if we can't check (might be configured)
        enketo_available = True
    
    context = {
        'forms': forms,
        'form_submissions': form_submissions,
        'enketo_available': enketo_available,
        'enketo_status_message': enketo_status_message,
    }
    return render(request, 'api/enketo_form_list.html', context)


def form_detail_view(request, form_id):
    """
    Display form details with submissions list.
    
    GET /forms/{form_id}/
    """
    try:
        form = FormDefinition.objects.get(id=form_id)
    except FormDefinition.DoesNotExist:
        return render(request, 'api/error.html', {
            'error': 'Form not found',
            'message': f'Form with ID {form_id} does not exist.'
        }, status=404)
    
    # Get all submissions for this form
    submissions = FormSubmission.objects.filter(form=form).order_by('-submitted_at')
    
    # Check if Enketo is available
    enketo_available = False
    enketo_status_message = None
    try:
        enketo_service = EnketoService()
        if enketo_service.enabled:
            # Enable button if Enketo is configured (even if not running)
            # The actual form rendering will handle connection errors gracefully
            enketo_available = True
            # Try to check connection (non-blocking, just for status message)
            try:
                enketo_service.check_connection()
            except EnketoConnectionError:
                enketo_status_message = (
                    "Note: Enketo Express may not be running. If you encounter errors, "
                    "please start Enketo Express on port 8005."
                )
            except Exception:
                pass  # Silently ignore other errors during status check
        else:
            enketo_status_message = "Enketo Express is not configured."
    except Exception as e:
        logger.warning(f"Could not check Enketo status: {str(e)}")
        # Still enable if we can't check (might be configured)
        enketo_available = True
    
    context = {
        'form': form,
        'submissions': submissions,
        'enketo_available': enketo_available,
        'enketo_status_message': enketo_status_message,
    }
    return render(request, 'api/form_detail.html', context)


def fill_form_view(request, form_id):
    """
    Redirect to Enketo to fill a new form.
    
    GET /forms/{form_id}/fill/
    """
    try:
        form = FormDefinition.objects.get(id=form_id)
    except FormDefinition.DoesNotExist:
        return render(request, 'api/error.html', {
            'error': 'Form not found',
            'message': f'Form with ID {form_id} does not exist.'
        }, status=404)
    
    try:
        enketo_service = EnketoService()
        
        # Check if Enketo is configured
        if not enketo_service.enabled:
            return render(request, 'api/error.html', {
                'error': 'Enketo Not Configured',
                'message': (
                    'Enketo Express is not configured. Please set the ENKETO_URL environment variable.\n\n'
                    'To configure Enketo:\n'
                    '1. Set ENKETO_URL (e.g., export ENKETO_URL=http://localhost:8005)\n'
                    '2. Optionally set ENKETO_API_TOKEN for authentication\n'
                    '3. Ensure Enketo Express service is running\n\n'
                    'For more information, see the documentation.'
                )
            }, status=503)
        
        # Build return URL for after submission
        site_url = getattr(settings, 'SITE_URL', request.build_absolute_uri('/').rstrip('/'))
        return_url = f"{site_url}/api/forms/submit/"
        
        # Render form in Enketo
        # Don't pass form_id - let it extract from XML to ensure consistency
        # The form_id in XML (e.g., awVr5i22y9sWTYd5KguiGr) is what Enketo uses
        result = enketo_service.render_form(
            form_xml=form.xml_content,
            instance_id=None,  # New form, no instance
            return_url=return_url
            # form_id will be extracted from XML automatically
        )
        
        enketo_url = result.get('url') or result.get('offline_url')
        
        if not enketo_url:
            raise EnketoFormRenderError("Enketo did not return a valid URL")
        
        logger.info(f"Redirecting to Enketo for form {form_id}: {enketo_url}")
        
        # Redirect to Enketo form
        return redirect(enketo_url)
        
    except EnketoConfigurationError as e:
        logger.error(f"Enketo configuration error for form {form_id}: {str(e)}")
        return render(request, 'api/error.html', {
            'error': 'Enketo Configuration Error',
            'message': str(e)
        }, status=503)
    
    except EnketoFormRenderError as e:
        logger.error(f"Failed to render form {form_id}: {str(e)}")
        return render(request, 'api/error.html', {
            'error': 'Form Rendering Error',
            'message': f'Failed to render form: {str(e)}'
        }, status=400)
    
    except EnketoConnectionError as e:
        logger.error(f"Enketo connection error for form {form_id}: {str(e)}")
        return render(request, 'api/error.html', {
            'error': 'Enketo Service Unavailable',
            'message': (
                f'Unable to connect to Enketo service.\n\n'
                f'{str(e)}\n\n'
                f'Please check:\n'
                f'1. Is Enketo Express running?\n'
                f'2. Is ENKETO_URL correctly configured?\n'
                f'3. Is the service accessible from this server?'
            )
        }, status=503)
    
    except EnketoServiceException as e:
        logger.error(f"Enketo service error for form {form_id}: {str(e)}")
        return render(request, 'api/error.html', {
            'error': 'Enketo Service Error',
            'message': f'Enketo service error: {str(e)}'
        }, status=503)
    
    except Exception as e:
        logger.error(f"Unexpected error rendering form {form_id}: {str(e)}")
        return render(request, 'api/error.html', {
            'error': 'Internal Error',
            'message': 'An unexpected error occurred while rendering the form.'
        }, status=500)


def edit_submission_view(request, submission_id):
    """
    Redirect to Enketo to edit an existing submission.
    
    GET /submissions/{submission_id}/edit/
    """
    try:
        submission = FormSubmission.objects.get(id=submission_id)
    except FormSubmission.DoesNotExist:
        return render(request, 'api/error.html', {
            'error': 'Submission not found',
            'message': f'Submission with ID {submission_id} does not exist.'
        }, status=404)
    
    # Check permissions - users can only edit their own submissions unless staff
    if not request.user.is_staff and not request.user.is_superuser:
        if submission.user != request.user:
            return render(request, 'api/error.html', {
                'error': 'Permission Denied',
                'message': 'You do not have permission to edit this submission.'
            }, status=403)
    
    try:
        enketo_service = EnketoService()
        
        # Check if Enketo is configured
        if not enketo_service.enabled:
            return render(request, 'api/error.html', {
                'error': 'Enketo Not Configured',
                'message': (
                    'Enketo Express is not configured. Please set the ENKETO_URL environment variable.\n\n'
                    'To configure Enketo:\n'
                    '1. Set ENKETO_URL (e.g., export ENKETO_URL=http://localhost:8005)\n'
                    '2. Optionally set ENKETO_API_TOKEN for authentication\n'
                    '3. Ensure Enketo Express service is running'
                )
            }, status=503)
        
        # Get the instance ID from submission data (Enketo instance ID)
        instance_id = submission.submission_data.get('__id') or submission.submission_data.get('meta', {}).get('instanceID')
        
        # If no instance ID, we need to create a new form with pre-filled data
        # For now, we'll render a new form and pass the data
        site_url = getattr(settings, 'SITE_URL', request.build_absolute_uri('/').rstrip('/'))
        return_url = f"{site_url}/api/submissions/{submission_id}/update/"
        
        # Render form in Enketo with instance ID for editing
        result = enketo_service.render_form(
            form_xml=submission.form.xml_content,
            instance_id=instance_id,
            return_url=return_url
            # form_id will be extracted from XML automatically
        )
        
        enketo_url = result.get('url') or result.get('offline_url')
        
        if not enketo_url:
            raise EnketoFormRenderError("Enketo did not return a valid URL")
        
        logger.info(f"Redirecting to Enketo for editing submission {submission_id}: {enketo_url}")
        
        # Redirect to Enketo form
        return redirect(enketo_url)
        
    except EnketoConfigurationError as e:
        logger.error(f"Enketo configuration error for submission {submission_id}: {str(e)}")
        return render(request, 'api/error.html', {
            'error': 'Enketo Configuration Error',
            'message': str(e)
        }, status=503)
    
    except EnketoFormRenderError as e:
        logger.error(f"Failed to render submission {submission_id} for editing: {str(e)}")
        return render(request, 'api/error.html', {
            'error': 'Form Rendering Error',
            'message': f'Failed to render form for editing: {str(e)}'
        }, status=400)
    
    except EnketoConnectionError as e:
        logger.error(f"Enketo connection error for submission {submission_id}: {str(e)}")
        return render(request, 'api/error.html', {
            'error': 'Enketo Service Unavailable',
            'message': (
                f'Unable to connect to Enketo service.\n\n'
                f'{str(e)}\n\n'
                f'Please check:\n'
                f'1. Is Enketo Express running?\n'
                f'2. Is ENKETO_URL correctly configured?\n'
                f'3. Is the service accessible from this server?'
            )
        }, status=503)
    
    except EnketoServiceException as e:
        logger.error(f"Enketo service error for submission {submission_id}: {str(e)}")
        return render(request, 'api/error.html', {
            'error': 'Enketo Service Error',
            'message': f'Enketo service error: {str(e)}'
        }, status=503)
    
    except Exception as e:
        logger.error(f"Unexpected error rendering submission {submission_id}: {str(e)}")
        return render(request, 'api/error.html', {
            'error': 'Internal Error',
            'message': 'An unexpected error occurred while rendering the form for editing.'
        }, status=500)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # Enketo will POST here, so we allow it
def submit_form_view(request):
    """
    Handle form submissions from Enketo.
    
    GET /api/forms/submit/ - Show submission success page
    POST /api/forms/submit/ - Receive submission data from Enketo
    """
    if request.method == 'GET':
        # Show success page or redirect
        return render(request, 'api/submission_success.html', {
            'message': 'Form submitted successfully!'
        })
    
    # Handle POST from Enketo
    try:
        # Enketo sends submission data in the request
        # The exact format depends on Enketo configuration
        submission_data = request.data.get('submission') or request.data.get('xml_submission_file')
        form_id = request.data.get('form_id') or request.GET.get('form_id')
        
        # If submission_data is XML, parse it
        if isinstance(submission_data, str) and submission_data.strip().startswith('<'):
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(submission_data)
                # Extract form ID from XML if not provided
                if not form_id:
                    form_id_attr = root.get('id')
                    if form_id_attr:
                        # Try to find form by kobo_id
                        try:
                            form = FormDefinition.objects.get(kobo_id=form_id_attr)
                            form_id = form.id
                        except FormDefinition.DoesNotExist:
                            pass
            except ET.ParseError:
                pass
        
        # If we still don't have form_id, try to get it from the submission data
        if not form_id and isinstance(submission_data, dict):
            form_id = submission_data.get('form_id')
        
        if not form_id:
            return Response({
                'success': False,
                'error': 'form_id is required',
                'error_code': 'missing_form_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            form = FormDefinition.objects.get(id=form_id)
        except FormDefinition.DoesNotExist:
            return Response({
                'success': False,
                'error': f'Form with ID {form_id} does not exist',
                'error_code': 'form_not_found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Create submission
        submission = FormSubmission.objects.create(
            form=form,
            user=request.user if request.user.is_authenticated else None,
            submission_data=submission_data if isinstance(submission_data, dict) else {'xml': submission_data},
            status='submitted'
        )
        
        logger.info(f"Form submission created: {submission.id} for form {form_id}")
        
        # Return success response
        return Response({
            'success': True,
            'submission_id': submission.id,
            'message': 'Form submitted successfully'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error processing form submission: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while processing the submission',
            'error_code': 'submission_error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # Enketo will POST here
def update_submission_view(request, submission_id):
    """
    Handle updated submissions from Enketo (for editing).
    
    POST /api/submissions/{submission_id}/update/
    """
    try:
        submission = FormSubmission.objects.get(id=submission_id)
    except FormSubmission.DoesNotExist:
        return Response({
            'success': False,
            'error': f'Submission with ID {submission_id} does not exist',
            'error_code': 'submission_not_found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check permissions
    if not request.user.is_staff and not request.user.is_superuser:
        if submission.user != request.user:
            return Response({
                'success': False,
                'error': 'You do not have permission to update this submission',
                'error_code': 'permission_denied'
            }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Get updated submission data from Enketo
        submission_data = request.data.get('submission') or request.data.get('xml_submission_file')
        
        # Update submission
        submission.submission_data = submission_data if isinstance(submission_data, dict) else {'xml': submission_data}
        submission.status = 'submitted'  # Reset to submitted when edited
        submission.save()
        
        logger.info(f"Submission {submission_id} updated successfully")
        
        return Response({
            'success': True,
            'submission_id': submission.id,
            'message': 'Submission updated successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error updating submission {submission_id}: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while updating the submission',
            'error_code': 'update_error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Legacy views for backward compatibility
class FormListView(generics.ListAPIView):
    """Legacy view - use FormDefinitionViewSet instead."""
    queryset = FormDefinition.objects.all()
    serializer_class = FormDefinitionSerializer
    pagination_class = StandardResultsSetPagination


class FormDetailView(generics.RetrieveAPIView):
    """Legacy view - use FormDefinitionViewSet instead."""
    queryset = FormDefinition.objects.all()
    serializer_class = FormDefinitionSerializer


# ============================================================================
# Kobo Import Views
# ============================================================================

def kobo_import_view(request):
    """
    Main page for importing forms and submissions from Kobo.
    """
    kobo_service = KoboService()
    kobo_configured = bool(kobo_service.access_token)
    
    # Get list of forms from Kobo if configured
    kobo_forms = []
    kobo_error = None
    if kobo_configured:
        try:
            kobo_forms_raw = kobo_service.list_forms()
            # Get existing forms in Django and create mapping
            django_forms = FormDefinition.objects.all().order_by('-created_at')
            kobo_to_django = {form.kobo_id: form for form in django_forms if form.kobo_id}
            
            # Add django_form reference to each kobo form for template
            for kobo_form in kobo_forms_raw:
                asset_id = kobo_form.get('uid') or kobo_form.get('id')
                if asset_id and asset_id in kobo_to_django:
                    kobo_form['django_form'] = kobo_to_django[asset_id]
                else:
                    kobo_form['django_form'] = None
            kobo_forms = kobo_forms_raw
        except Exception as e:
            kobo_error = str(e)
            logger.error(f"Failed to fetch Kobo forms: {str(e)}")
            django_forms = FormDefinition.objects.all().order_by('-created_at')
    else:
        django_forms = FormDefinition.objects.all().order_by('-created_at')
    
    context = {
        'kobo_configured': kobo_configured,
        'kobo_forms': kobo_forms,
        'kobo_error': kobo_error,
        'django_forms': django_forms,
        'kobo_api_url': kobo_service.api_base_url,
    }
    
    return render(request, 'api/kobo_import.html', context)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def kobo_import_form_view(request):
    """
    Import a form from Kobo into Django.
    
    POST /api/kobo/import-form/
    Body: {"asset_id": "abc123", "overwrite": false}
    """
    try:
        asset_id = request.data.get('asset_id')
        if not asset_id:
            return Response({
                'success': False,
                'error': 'asset_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        overwrite = request.data.get('overwrite', False)
        
        kobo_service = KoboService()
        result = kobo_service.import_form(asset_id, overwrite=overwrite)
        
        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED if result['action'] == 'created' else status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error importing form from Kobo: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def kobo_import_submissions_view(request):
    """
    Import submissions from Kobo into Django.
    
    POST /api/kobo/import-submissions/
    Body: {"asset_id": "abc123", "form_id": 1, "limit": 100}
    """
    try:
        asset_id = request.data.get('asset_id')
        form_id = request.data.get('form_id')
        limit = request.data.get('limit')
        
        if not asset_id:
            return Response({
                'success': False,
                'error': 'asset_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get form if form_id provided, otherwise will be found by asset_id
        form = None
        if form_id:
            try:
                form = FormDefinition.objects.get(id=form_id)
            except FormDefinition.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'Form with ID {form_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        kobo_service = KoboService()
        result = kobo_service.import_submissions(
            asset_id,
            form=form,
            limit=limit,
            user=request.user
        )
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error importing submissions from Kobo: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kobo_list_forms_view(request):
    """
    Get list of forms from Kobo API.
    
    GET /api/kobo/forms/
    """
    try:
        kobo_service = KoboService()
        forms = kobo_service.list_forms()
        
        return Response({
            'success': True,
            'forms': forms,
            'count': len(forms)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error fetching forms from Kobo: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)