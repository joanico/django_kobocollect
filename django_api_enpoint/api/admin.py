from django.contrib import admin
from django.utils.html import format_html
from django import forms
from django.core.exceptions import ValidationError
import os
import tempfile
from .models import (
    Beneficiary, Municipality, PostAdmin, Suco,
    FormDefinition, FormSubmission, FormMedia
)


@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = ['date', 'name', 'municipality', 'postadmin', 'suco']
    list_filter = ['name']


@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(PostAdmin)
class PostAdmin(admin.ModelAdmin):
    list_display = ['name', 'municipality']


@admin.register(Suco)
class SucoAdmin(admin.ModelAdmin):
    list_display = ['name', 'postadmin']


class FormDefinitionAdminForm(forms.ModelForm):
    """Custom form for FormDefinition with XLSForm upload support."""
    xlsform_file = forms.FileField(
        required=False,
        help_text='Upload an XLSForm (XLS/XLSX) file. It will be automatically converted to XML. '
                  'If both XLSForm file and XML content are provided, XLSForm takes priority.'
    )
    
    class Meta:
        model = FormDefinition
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make xml_content optional in the form (it will be set from XLSForm if needed)
        self.fields['xml_content'].required = False
        self.fields['xml_content'].help_text = (
            'Paste XForm XML content here. '
            'Leave empty if uploading an XLSForm file above.'
        )
    
    def clean(self):
        cleaned_data = super().clean()
        xlsform_file = cleaned_data.get('xlsform_file')
        xml_content = cleaned_data.get('xml_content')
        
        # Ensure at least one method is provided
        if not xlsform_file and not xml_content:
            raise ValidationError({
                'xlsform_file': 'Either upload an XLSForm file OR provide XML content. At least one is required.',
                'xml_content': 'Either upload an XLSForm file OR provide XML content. At least one is required.'
            })
        
        # If XLSForm is uploaded, validate it
        if xlsform_file:
            # Check file extension
            file_name = xlsform_file.name.lower()
            if not (file_name.endswith('.xls') or file_name.endswith('.xlsx')):
                raise ValidationError({
                    'xlsform_file': 'Please upload a valid XLSForm file (.xls or .xlsx)'
                })
        
        return cleaned_data


@admin.register(FormDefinition)
class FormDefinitionAdmin(admin.ModelAdmin):
    """Admin interface for Form Definition model."""
    form = FormDefinitionAdminForm
    list_display = ['name', 'kobo_id', 'version', 'created_at', 'updated_at', 'submission_count']
    list_filter = ['version', 'created_at', 'updated_at']
    search_fields = ['name', 'kobo_id', 'version']
    readonly_fields = ['created_at', 'updated_at', 'xml_preview']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'kobo_id', 'version')
        }),
        ('Form Content - Choose One Method', {
            'fields': ('xlsform_file', 'xml_content'),
            'description': 'Either upload an XLSForm file (XLS/XLSX) OR paste XForm XML content. '
                          'If both are provided, XLSForm will be converted and used. '
                          'XML content is optional when uploading an XLSForm file.'
        }),
        ('XML Preview', {
            'fields': ('xml_preview',),
            'classes': ('collapse',),
            'description': 'Read-only preview of the XML content (first 1000 characters).'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Override save to handle XLSForm conversion."""
        xlsform_file = form.cleaned_data.get('xlsform_file')
        
        # If XLSForm file is uploaded, convert it to XML
        if xlsform_file:
            try:
                xml_content = self._convert_xlsform_to_xml(xlsform_file)
                obj.xml_content = xml_content
            except Exception as e:
                from django.contrib import messages
                messages.error(
                    request,
                    f'Error converting XLSForm to XML: {str(e)}. '
                    f'Please ensure pyxform is installed: pip install pyxform'
                )
                raise
        
        super().save_model(request, obj, form, change)
    
    def _convert_xlsform_to_xml(self, xlsform_file):
        """
        Convert XLSForm file to XForm XML.
        
        Args:
            xlsform_file: Uploaded XLSForm file
            
        Returns:
            str: XForm XML content
            
        Raises:
            ImportError: If pyxform is not installed
            Exception: If conversion fails
        """
        try:
            from pyxform import create_survey_from_xls
        except ImportError:
            raise ImportError(
                'pyxform is required to convert XLSForm to XML. '
                'Install it with: pip install pyxform'
            )
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx' if xlsform_file.name.endswith('.xlsx') else '.xls') as tmp_file:
            for chunk in xlsform_file.chunks():
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name
        
        try:
            # Create survey object directly from XLSForm file
            survey = create_survey_from_xls(tmp_file_path)
            
            # Convert to XML
            xml_content = survey.to_xml()
            
            return xml_content
            
        except Exception as e:
            raise Exception(f'Failed to convert XLSForm: {str(e)}')
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    def submission_count(self, obj):
        """Display the number of submissions for this form."""
        return obj.formsubmission_set.count()
    submission_count.short_description = 'Submissions'
    
    def xml_preview(self, obj):
        """Show a preview of the XML content."""
        if obj.xml_content:
            preview = obj.xml_content[:1000]
            if len(obj.xml_content) > 1000:
                preview += '\n\n... (truncated, full XML available in xml_content field above)'
            # Escape HTML for safety
            from django.utils.html import escape
            escaped_preview = escape(preview)
            return format_html(
                '<pre style="white-space: pre-wrap; background: #f5f5f5; padding: 10px; border: 1px solid #ddd; max-height: 400px; overflow-y: auto; font-family: monospace;">{}</pre>',
                escaped_preview
            )
        return 'No XML content'
    xml_preview.short_description = 'XML Preview'


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    """Admin interface for Form Submission model."""
    list_display = ['id', 'form', 'submission_summary', 'status', 'submitted_at', 'user']
    list_filter = ['status', 'submitted_at', 'form']
    search_fields = ['form__name', 'form__kobo_id', 'user__username', 'submission_data']
    readonly_fields = ['submitted_at']
    date_hierarchy = 'submitted_at'
    list_per_page = 25
    fieldsets = (
        ('Submission Information', {
            'fields': ('form', 'user', 'status')
        }),
        ('Submission Data', {
            'fields': ('submission_data',),
            'description': 'JSON data submitted for this form.'
        }),
        ('Timestamps', {
            'fields': ('submitted_at',),
            'classes': ('collapse',)
        }),
    )
    
    def submission_summary(self, obj):
        """Show a summary of submission data in the list view."""
        if obj.submission_data:
            # Try to extract name or first field value
            data = obj.submission_data
            if isinstance(data, dict):
                # Look for common name fields
                name = data.get('Naran') or data.get('name') or data.get('Name') or data.get('naran')
                if name:
                    return f"{name}"
                # Otherwise show first few key-value pairs
                items = list(data.items())[:2]
                return ", ".join([f"{k}: {v}" for k, v in items])
        return "No data"
    submission_summary.short_description = 'Submission Data'
    
    def get_readonly_fields(self, request, obj=None):
        """Make submission_data readonly when viewing existing submissions."""
        if obj:  # editing an existing object
            return self.readonly_fields + ('submission_data',)
        return self.readonly_fields


@admin.register(FormMedia)
class FormMediaAdmin(admin.ModelAdmin):
    """Admin interface for Form Media model."""
    list_display = ['filename', 'form', 'uploaded_at']
    list_filter = ['uploaded_at', 'form']
    search_fields = ['filename', 'form__name', 'form__kobo_id']
    readonly_fields = ['uploaded_at']
    date_hierarchy = 'uploaded_at'
