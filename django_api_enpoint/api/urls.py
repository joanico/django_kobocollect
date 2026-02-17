"""
URL configuration for API endpoints.

This module defines all API routes including form management,
submission handling, and media file management.

API URL Structure:
==================

Forms (Form Definitions):
  GET    /api/forms/                    - List all form definitions
  POST   /api/forms/                    - Create a new form definition
  GET    /api/forms/{id}/               - Get a specific form definition
  PUT    /api/forms/{id}/                - Update a form definition
  DELETE /api/forms/{id}/                - Delete a form definition
  POST   /api/forms/{id}/render/         - Render form via Enketo
  GET    /api/forms/{id}/submissions/    - Get all submissions for a form

Submissions (Form Submissions):
  GET    /api/submissions/               - List all form submissions
  POST   /api/submissions/               - Create a new submission
  POST   /api/submissions/submit/        - Submit a form (alternative endpoint)
  GET    /api/submissions/{id}/          - Get a specific submission
  PUT    /api/submissions/{id}/          - Update a submission
  DELETE /api/submissions/{id}/          - Delete a submission
  POST   /api/submissions/{id}/update_status/ - Update submission status

Media Files:
  GET    /api/media/                    - List all media files
  POST   /api/media/                    - Upload a media file
  GET    /api/media/{id}/               - Get a specific media file
  DELETE /api/media/{id}/               - Delete a media file
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register viewsets
# Using descriptive basenames for clearer URL reverse names
router = DefaultRouter()
router.register(r'forms', views.FormDefinitionViewSet, basename='form-definition')
router.register(r'submissions', views.FormSubmissionViewSet, basename='form-submission')
router.register(r'media', views.FormMediaViewSet, basename='form-media')

urlpatterns = [
    # API Root with clear documentation
    path('', views.api_root, name='api-root'),
    
    # Enketo Form Submission Handlers
    path('forms/submit/', views.submit_form_view, name='submit-form'),
    path('submissions/<int:submission_id>/update/', views.update_submission_view, name='update-submission'),
    
    # Kobo Import Endpoints
    path('kobo/forms/', views.kobo_list_forms_view, name='kobo-list-forms'),
    path('kobo/import-form/', views.kobo_import_form_view, name='kobo-import-form'),
    path('kobo/import-submissions/', views.kobo_import_submissions_view, name='kobo-import-submissions'),
    
    # Router URLs for ViewSets (primary implementation)
    # These create: /forms/, /forms/{pk}/, /submissions/, etc.
    path('', include(router.urls)),
    
    # Legacy view for backward compatibility (moved after router)
    # Note: This will be at /api/ but router's API root takes precedence
    # If you need the legacy view, access it via a different path
    # path('legacy/', views.GetKoboApi, name='aplikante'),
    
    # Legacy API endpoints for backward compatibility
    # Note: These are shadowed by router patterns above and will not be reached.
    # They are kept for reference but should be removed in future versions.
    # If legacy endpoints are needed, use different paths like /legacy/forms/
    # path('legacy/forms/', views.FormListView.as_view(), name='form-list-legacy'),
    # path('legacy/forms/<int:pk>/', views.FormDetailView.as_view(), name='form-detail-legacy'),
]
