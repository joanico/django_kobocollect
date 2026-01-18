"""django_api_enpoint URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from api import views as api_views
from api import openrosa_views

urlpatterns = [
    path('api/', include('api.urls')),
    path('admin/', admin.site.urls),
    
    # OpenRosa Protocol Endpoints (for Enketo Express)
    # These must be at root level as Enketo calls them using server_url
    path('formList', openrosa_views.form_list, name='openrosa-form-list'),
    path('forms/<str:form_id>/form.xml', openrosa_views.form_xml, name='openrosa-form-xml'),
    path('forms/<str:form_id>/manifest.xml', openrosa_views.form_manifest, name='openrosa-form-manifest'),
    path('submission', openrosa_views.submission, name='openrosa-submission'),
    
    # Enketo Form Interface URLs
    path('forms/', api_views.form_list_view, name='form-list'),
    path('forms/<int:form_id>/', api_views.form_detail_view, name='form-detail'),
    path('forms/<int:form_id>/fill/', api_views.fill_form_view, name='fill-form'),
    path('submissions/<int:submission_id>/edit/', api_views.edit_submission_view, name='edit-submission'),
    
    # Kobo Import Interface
    path('kobo/import/', api_views.kobo_import_view, name='kobo-import'),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
