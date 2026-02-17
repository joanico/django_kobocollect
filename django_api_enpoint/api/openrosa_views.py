"""
OpenRosa Protocol Views for Enketo Express Integration.

OpenRosa is a protocol for form management. Enketo Express uses this protocol
to fetch form definitions from the server. This module implements the required
OpenRosa endpoints.

OpenRosa Endpoints:
- GET /formList - Returns list of available forms
- GET /forms/{form_id}/form.xml - Returns the XForm XML
- GET /forms/{form_id}/manifest.xml - Returns the form manifest (optional)
- POST /submission - Receives form submissions
"""
import logging
import xml.etree.ElementTree as ET
from django.http import HttpResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import FormDefinition, FormSubmission

logger = logging.getLogger(__name__)


@require_http_methods(["GET", "HEAD"])
@csrf_exempt
def form_list(request):
    """
    OpenRosa formList endpoint.
    
    Returns an XML list of available forms in OpenRosa format.
    Enketo Express calls this to discover available forms.
    
    Query parameters:
    - formID: Optional form ID to filter results
    
    Returns:
    - XML response in OpenRosa formList format (or empty body for HEAD requests)
    """
    form_id = request.GET.get('formID')
    
    if form_id:
        # Return single form if formID is specified
        # Try to find by kobo_id first, then try to find by XML form ID
        try:
            form = FormDefinition.objects.get(kobo_id=form_id)
            forms = [form]
        except FormDefinition.DoesNotExist:
            # Try to find by XML form ID (the id attribute in the root instance element)
            import xml.etree.ElementTree as ET
            forms = []
            for form in FormDefinition.objects.all():
                try:
                    root = ET.fromstring(form.xml_content)
                    xml_form_id = None
                    for instance in root.findall('.//{http://www.w3.org/2002/xforms}instance'):
                        if len(instance) > 0:
                            first = instance[0]
                            xml_form_id = first.get('id')
                            if not xml_form_id:
                                xml_form_id = first.tag
                                if '}' in xml_form_id:
                                    xml_form_id = xml_form_id.split('}')[-1]
                            break
                    if xml_form_id == form_id:
                        forms = [form]
                        break
                except ET.ParseError:
                    continue
    else:
        # Return all forms
        forms = FormDefinition.objects.all()
    
    # Build OpenRosa formList XML
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<xforms xmlns="http://openrosa.org/xforms/xformsList">',
    ]
    
    for form in forms:
        # Extract form name from XML or use model name
        form_name = form.name
        
        # Extract form ID from XML (the id attribute in the root instance element)
        # This is what Enketo uses to identify forms
        import xml.etree.ElementTree as ET
        xml_form_id = form.kobo_id  # Default to kobo_id
        try:
            root = ET.fromstring(form.xml_content)
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
            # If XML parsing fails, use kobo_id
            pass
        
        # Build form URL - Use XML form ID in URL so Enketo can find it
        site_url = request.build_absolute_uri('/').rstrip('/')
        download_url = f"{site_url}/forms/{xml_form_id}/form.xml"
        manifest_url = f"{site_url}/forms/{xml_form_id}/manifest.xml"
        
        xml_parts.extend([
            '<xform>',
            f'<formID>{xml_form_id}</formID>',  # Use XML form ID, not kobo_id
            f'<name>{form_name}</name>',
            f'<version>{form.version}</version>',
            f'<hash>md5:{xml_form_id}</hash>',
            f'<downloadUrl>{download_url}</downloadUrl>',
            f'<manifestUrl>{manifest_url}</manifestUrl>',
            '</xform>',
        ])
    
    xml_parts.append('</xforms>')
    xml_content = '\n'.join(xml_parts)
    
    # For HEAD requests, return empty body but with proper headers
    if request.method == 'HEAD':
        response = HttpResponse(content_type='text/xml; charset=utf-8')
    else:
        response = HttpResponse(xml_content, content_type='text/xml; charset=utf-8')
    
    # OpenRosa requires specific headers
    response['X-OpenRosa-Version'] = '1.0'
    return response


@require_http_methods(["GET", "HEAD"])
@csrf_exempt
def form_xml(request, form_id):
    """
    OpenRosa form XML endpoint.
    
    Returns the XForm XML for a specific form.
    Enketo Express calls this to get the form definition.
    
    Args:
    - form_id: The form ID (kobo_id or XML form ID) to retrieve
    
    Returns:
    - XForm XML content
    """
    # Try to find by kobo_id first, then try to find by XML form ID
    try:
        form = FormDefinition.objects.get(kobo_id=form_id)
    except FormDefinition.DoesNotExist:
        # Try to find by XML form ID (the id attribute in the root instance element)
        import xml.etree.ElementTree as ET
        form = None
        for f in FormDefinition.objects.all():
            try:
                root = ET.fromstring(f.xml_content)
                xml_form_id = None
                for instance in root.findall('.//{http://www.w3.org/2002/xforms}instance'):
                    if len(instance) > 0:
                        first = instance[0]
                        xml_form_id = first.get('id')
                        if not xml_form_id:
                            xml_form_id = first.tag
                            if '}' in xml_form_id:
                                xml_form_id = xml_form_id.split('}')[-1]
                        break
                if xml_form_id == form_id:
                    form = f
                    break
            except ET.ParseError:
                continue
        
        if form is None:
            raise Http404(f"Form with ID '{form_id}' not found")
    
    # For HEAD requests, return empty body but with proper headers
    if request.method == 'HEAD':
        response = HttpResponse(content_type='text/xml; charset=utf-8')
    else:
        response = HttpResponse(form.xml_content, content_type='text/xml; charset=utf-8')
    
    response['X-OpenRosa-Version'] = '1.0'
    return response


@require_http_methods(["GET", "HEAD"])
@csrf_exempt
def form_manifest(request, form_id):
    """
    OpenRosa form manifest endpoint.
    
    Returns the manifest XML for a specific form (media files, etc.).
    This is optional but Enketo may request it.
    
    Args:
    - form_id: The form ID (kobo_id or XML form ID) to retrieve manifest for
    
    Returns:
    - Manifest XML content (empty manifest if no media)
    """
    # Try to find by kobo_id first, then try to find by XML form ID
    try:
        form = FormDefinition.objects.get(kobo_id=form_id)
    except FormDefinition.DoesNotExist:
        # Try to find by XML form ID (the id attribute in the root instance element)
        import xml.etree.ElementTree as ET
        form = None
        for f in FormDefinition.objects.all():
            try:
                root = ET.fromstring(f.xml_content)
                xml_form_id = None
                for instance in root.findall('.//{http://www.w3.org/2002/xforms}instance'):
                    if len(instance) > 0:
                        first = instance[0]
                        xml_form_id = first.get('id')
                        if not xml_form_id:
                            xml_form_id = first.tag
                            if '}' in xml_form_id:
                                xml_form_id = xml_form_id.split('}')[-1]
                        break
                if xml_form_id == form_id:
                    form = f
                    break
            except ET.ParseError:
                continue
        
        if form is None:
            raise Http404(f"Form with ID '{form_id}' not found")
    
    # For now, return empty manifest (no media files)
    # TODO: Implement media file support if needed
    manifest_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<manifest xmlns="http://openrosa.org/xforms/xformsManifest">
</manifest>'''
    
    # For HEAD requests, return empty body but with proper headers
    if request.method == 'HEAD':
        response = HttpResponse(content_type='text/xml; charset=utf-8')
    else:
        response = HttpResponse(manifest_xml, content_type='text/xml; charset=utf-8')
    
    response['X-OpenRosa-Version'] = '1.0'
    return response


@require_http_methods(["POST"])
@csrf_exempt
def submission(request):
    """
    OpenRosa submission endpoint.
    
    Receives form submissions from Enketo Express in OpenRosa format.
    The submission is sent as multipart/form-data with:
    - xml_submission_file: The XML submission data
    - Headers: X-OpenRosa-Version, X-OpenRosa-Instance-Id, X-OpenRosa-Deprecated-Id
    
    Returns:
    - OpenRosa XML response with status 201 for success
    """
    # Check content type
    content_type = request.META.get('CONTENT_TYPE', '')
    if not content_type.startswith('multipart/form-data'):
        response = HttpResponse(
            '''<?xml version="1.0" encoding="UTF-8"?>
<OpenRosaResponse xmlns="http://openrosa.org/http/response" items="0">
    <message nature="error">Required multipart POST field xml_submission_file missing.</message>
</OpenRosaResponse>''',
            content_type='text/xml; charset=utf-8',
            status=400
        )
        response['X-OpenRosa-Version'] = '1.0'
        return response
    
    # Get submission XML from request
    if 'xml_submission_file' not in request.FILES:
        response = HttpResponse(
            '''<?xml version="1.0" encoding="UTF-8"?>
<OpenRosaResponse xmlns="http://openrosa.org/http/response" items="0">
    <message nature="error">Required multipart POST field xml_submission_file missing.</message>
</OpenRosaResponse>''',
            content_type='text/xml; charset=utf-8',
            status=400
        )
        response['X-OpenRosa-Version'] = '1.0'
        return response
    
    xml_file = request.FILES['xml_submission_file']
    xml_content = xml_file.read().decode('utf-8')
    
    # Get instance ID from headers
    instance_id = request.META.get('HTTP_X_OPENROSA_INSTANCE_ID', '')
    deprecated_id = request.META.get('HTTP_X_OPENROSA_DEPRECATED_ID', '')
    
    try:
        # Parse XML to extract form ID
        root = ET.fromstring(xml_content)
        form_id_from_xml = root.get('id')
        
        if not form_id_from_xml:
            # Try to get from the root element name
            form_id_from_xml = root.tag
            if '}' in form_id_from_xml:
                form_id_from_xml = form_id_from_xml.split('}')[-1]
        
        # Find the form by XML form ID
        form = None
        for f in FormDefinition.objects.all():
            try:
                form_root = ET.fromstring(f.xml_content)
                xml_form_id = None
                for instance in form_root.findall('.//{http://www.w3.org/2002/xforms}instance'):
                    if len(instance) > 0:
                        first = instance[0]
                        xml_form_id = first.get('id')
                        if not xml_form_id:
                            xml_form_id = first.tag
                            if '}' in xml_form_id:
                                xml_form_id = xml_form_id.split('}')[-1]
                        break
                if xml_form_id == form_id_from_xml:
                    form = f
                    break
            except ET.ParseError:
                continue
        
        if form is None:
            logger.warning(f"Form not found for XML form ID: {form_id_from_xml}")
            response = HttpResponse(
                f'''<?xml version="1.0" encoding="UTF-8"?>
<OpenRosaResponse xmlns="http://openrosa.org/http/response" items="0">
    <message nature="error">Form with ID '{form_id_from_xml}' not found.</message>
</OpenRosaResponse>''',
                content_type='text/xml; charset=utf-8',
                status=404
            )
            response['X-OpenRosa-Version'] = '1.0'
            return response
        
        # Parse submission data from XML - convert to a simple dict structure
        # Store the raw XML and extract key fields
        submission_data = {
            '_xml': xml_content,
            '_instance_id': instance_id,
            '_deprecated_id': deprecated_id,
        }
        
        # Extract data fields from XML (simple approach - get all text nodes)
        def extract_text(elem, path=''):
            """Recursively extract text from XML elements"""
            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            current_path = f"{path}/{tag_name}" if path else tag_name
            
            if elem.text and elem.text.strip():
                submission_data[current_path] = elem.text.strip()
            
            for child in elem:
                extract_text(child, current_path)
        
        extract_text(root)
        
        # Create FormSubmission
        submission_obj = FormSubmission.objects.create(
            form=form,
            submission_data=submission_data,
            status='submitted'
        )
        
        logger.info(f"Form submission created: {submission_obj.id} for form {form.id}")
        
        # Return OpenRosa success response
        response = HttpResponse(
            f'''<?xml version="1.0" encoding="UTF-8"?>
<OpenRosaResponse xmlns="http://openrosa.org/http/response" items="1">
    <message nature="success">Form submission received successfully.</message>
</OpenRosaResponse>''',
            content_type='text/xml; charset=utf-8',
            status=201
        )
        response['X-OpenRosa-Version'] = '1.0'
        return response
        
    except ET.ParseError as e:
        logger.error(f"Error parsing submission XML: {str(e)}")
        response = HttpResponse(
            f'''<?xml version="1.0" encoding="UTF-8"?>
<OpenRosaResponse xmlns="http://openrosa.org/http/response" items="0">
    <message nature="error">Invalid XML format: {str(e)}</message>
</OpenRosaResponse>''',
            content_type='text/xml; charset=utf-8',
            status=400
        )
        response['X-OpenRosa-Version'] = '1.0'
        return response
    except Exception as e:
        logger.error(f"Error processing submission: {str(e)}", exc_info=True)
        response = HttpResponse(
            f'''<?xml version="1.0" encoding="UTF-8"?>
<OpenRosaResponse xmlns="http://openrosa.org/http/response" items="0">
    <message nature="error">Internal server error: {str(e)}</message>
</OpenRosaResponse>''',
            content_type='text/xml; charset=utf-8',
            status=500
        )
        response['X-OpenRosa-Version'] = '1.0'
        return response
