# Django Integration Guide

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [Models and Database](#models-and-database)
5. [API Endpoints](#api-endpoints)
6. [Usage Guide](#usage-guide)
7. [Workflows](#workflows)
8. [Services](#services)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This guide explains how Django integrates with Enketo Express and Kobo Toolbox to provide a complete form management and data collection solution.

### What This Integration Provides

- **Form Management**: Store and manage form definitions (XForm XML)
- **Data Collection**: Collect form submissions through Enketo Express
- **Kobo Integration**: Import forms and data from Kobo Toolbox
- **API Access**: RESTful API for programmatic access
- **User Interface**: Web interface for managing forms and viewing submissions

### Key Components

1. **Django Backend**: Handles form storage, data processing, and API endpoints
2. **Enketo Express**: Renders forms and handles user input
3. **Kobo Toolbox**: Source for form definitions and optional data sync

---

## Architecture

### High-Level Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Kobo Toolbox  │         │  Django Backend  │         │ Enketo Express  │
│                 │         │                  │         │                 │
│ • Form Storage  │────────▶│ • Form Storage   │────────▶│ • Form Rendering│
│ • Data Storage  │         │ • Data Processing│         │ • User Interface│
│ • API Access    │         │ • User Auth      │         │ • Data Entry    │
└─────────────────┘         └──────────────────┘         └─────────────────┘
         ▲                                                         │
         │                                                         │
         └─────────────────────────────────────────────────────────┘
                            (Submissions flow back)
```

### Data Flow

1. **Form Import**: Forms are imported from Kobo Toolbox into Django
2. **Form Storage**: Forms are stored in Django database as `FormDefinition` objects
3. **Form Rendering**: Django sends form XML to Enketo Express for rendering
4. **Data Collection**: Users fill out forms using Enketo Express interface
5. **Data Submission**: Submissions are sent back to Django
6. **Data Storage**: Submissions are stored in Django database as `FormSubmission` objects
7. **Optional Sync**: Data can be synced back to Kobo Toolbox if needed

### Component Responsibilities

**Django Backend:**
- Form management and storage
- User authentication and authorization
- Data processing and validation
- API endpoints for Enketo integration
- File upload handling
- Kobo API integration

**Enketo Express:**
- XForm rendering and display
- Client-side form validation
- Offline data collection
- Media file handling
- Form submission

**Kobo Toolbox:**
- Form definition source
- Optional data destination
- User management (if using Kobo accounts)

---

## Configuration

### Environment Variables

Create a `.env` file in `django_api_enpoint/` directory:

```bash
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database Configuration
DB_NAME=kobo_db
DB_HOST=127.0.0.1
DB_PORT=5433

# Enketo Express Configuration
ENKETO_URL=http://localhost:8005
ENKETO_API_TOKEN=dev_token_12345
SITE_URL=http://localhost:8000
ENKETO_REQUEST_TIMEOUT=30

# Kobo Toolbox Configuration
KOBO_API_BASE_URL=https://kf.kobotoolbox.org/api/v2
ACCESS_TOKEN=your_kobo_token
KOBO_DEFAULT_ASSET_ID=your_asset_id_here
KOBO_REQUEST_TIMEOUT=30
```

### Configuration Options

#### Enketo Express Configuration

- **ENKETO_URL** (Required): URL where Enketo Express is running
  - Local: `http://localhost:8005`
  - Production: `https://enketo.yourdomain.com`

- **ENKETO_API_TOKEN** (Optional but recommended): API token for authentication
  - Must match the API key in Enketo's `config/config.json`
  - For local development, can use: `dev_token_12345`
  - For production, use a secure token

- **SITE_URL** (Optional): Base URL of your Django application
  - Used for building return URLs after form submission
  - Defaults to auto-detection if not set

- **ENKETO_REQUEST_TIMEOUT** (Optional): Request timeout in seconds
  - Default: 30 seconds

#### Kobo Toolbox Configuration

- **KOBO_API_BASE_URL** (Optional): Kobo API base URL
  - Default: `https://kf.kobotoolbox.org/api/v2`
  - Alternative: `https://kobo.humanitarianresponse.info/api/v2`

- **ACCESS_TOKEN** (Required for Kobo integration): Your Kobo API token
  - Get from: Kobo Toolbox → Account Settings → API Tokens

- **KOBO_DEFAULT_ASSET_ID** (Optional): Default asset ID for data fetching
  - Found in Kobo form URL: `#/forms/{asset_id}`

- **KOBO_REQUEST_TIMEOUT** (Optional): Request timeout in seconds
  - Default: 30 seconds

### Verifying Configuration

```bash
python manage.py shell
```

```python
from django.conf import settings

print("ENKETO_URL:", getattr(settings, 'ENKETO_URL', 'Not set'))
print("ENKETO_API_TOKEN:", "Set" if getattr(settings, 'ENKETO_API_TOKEN', None) else "Not set")
print("SITE_URL:", getattr(settings, 'SITE_URL', 'Not set'))
print("ACCESS_TOKEN:", "Set" if getattr(settings, 'ACCESS_TOKEN', None) else "Not set")
```

---

## Models and Database

### FormDefinition Model

Stores form definitions (XForm XML templates).

**Fields:**
- `id`: Primary key (auto-generated)
- `name`: Form name (CharField, max 200 chars)
- `kobo_id`: Unique identifier from Kobo (CharField, max 100 chars, unique)
- `xml_content`: XForm XML content (TextField)
- `version`: Form version (CharField, max 20 chars, default "1.0")
- `created_at`: Creation timestamp (DateTimeField, auto-created)
- `updated_at`: Last update timestamp (DateTimeField, auto-updated)
- `is_active`: Whether form is active (BooleanField, default True)

**Usage:**
```python
from api.models import FormDefinition

# Create a form
form = FormDefinition.objects.create(
    name="Survey Form",
    kobo_id="survey_001",
    xml_content="<h:html>...</h:html>",
    version="1.0"
)

# Get all active forms
forms = FormDefinition.objects.filter(is_active=True)

# Get form by kobo_id
form = FormDefinition.objects.get(kobo_id="survey_001")
```

### FormSubmission Model

Stores form submissions from users.

**Fields:**
- `id`: Primary key (auto-generated)
- `form`: Foreign key to FormDefinition (required)
- `user`: Foreign key to User (optional, nullable)
- `submission_data`: JSON data from form submission (JSONField)
- `submitted_at`: Submission timestamp (DateTimeField, auto-created)
- `status`: Submission status (CharField, choices: draft, submitted, validated, rejected)

**Usage:**
```python
from api.models import FormSubmission, FormDefinition

# Get form
form = FormDefinition.objects.get(id=1)

# Create submission
submission = FormSubmission.objects.create(
    form=form,
    submission_data={"name": "John Doe", "age": "30"},
    status="submitted"
)

# Get all submissions for a form
submissions = FormSubmission.objects.filter(form=form)

# Filter by status
submitted = FormSubmission.objects.filter(status="submitted")
```

### FormMedia Model

Stores media files associated with forms (images, audio, video).

**Fields:**
- `id`: Primary key (auto-generated)
- `form`: Foreign key to FormDefinition (required)
- `file`: File field (FileField, uploads to 'form_media/')
- `filename`: Original filename (CharField, max 255 chars)
- `uploaded_at`: Upload timestamp (DateTimeField, auto-created)

---

## API Endpoints

### Form Endpoints

#### List All Forms

```http
GET /api/forms/
```

**Response:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Sample Survey Form",
      "kobo_id": "sample_form_001",
      "version": "1.0",
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z",
      "submission_count": 5
    }
  ]
}
```

#### Get Form Details

```http
GET /api/forms/{id}/
```

#### Create Form

```http
POST /api/forms/
Content-Type: application/json

{
  "name": "Survey Form",
  "kobo_id": "survey_001",
  "xml_content": "<?xml version=\"1.0\"?>...",
  "version": "1.0"
}
```

#### Render Form via Enketo

```http
POST /api/forms/{id}/render/
```

Returns Enketo form URL for rendering.

### Submission Endpoints

#### List All Submissions

```http
GET /api/submissions/
```

**Query Parameters:**
- `form`: Filter by form ID
- `status`: Filter by status (draft, submitted, validated, rejected)
- `page`: Page number for pagination
- `page_size`: Items per page

**Example:**
```http
GET /api/submissions/?form=1&status=submitted
```

#### Get Submission Details

```http
GET /api/submissions/{id}/
```

#### Submit Form Data

```http
POST /api/submissions/submit/
Content-Type: application/json

{
  "form_id": 1,
  "submission_data": {
    "name": "John Doe",
    "age": "30"
  },
  "status": "submitted"
}
```

#### Update Submission Status

```http
POST /api/submissions/{id}/update_status/
Content-Type: application/json

{
  "status": "approved"
}
```

### Kobo Integration Endpoints

#### List Forms from Kobo

```http
GET /api/kobo/forms/
Authorization: Token your_django_auth_token
```

#### Import Form from Kobo

```http
POST /api/kobo/import-form/
Content-Type: application/json
Authorization: Token your_django_auth_token

{
  "asset_id": "abc123",
  "overwrite": false
}
```

#### Import Submissions from Kobo

```http
POST /api/kobo/import-submissions/
Content-Type: application/json
Authorization: Token your_django_auth_token

{
  "asset_id": "abc123",
  "form_id": 1,
  "limit": 100
}
```

---

## Usage Guide

### Creating a Form Definition

#### Method 1: Using Django Admin (Recommended)

1. Go to `http://localhost:8000/admin/`
2. Navigate to **API** → **Form definitions**
3. Click **"Add Form definition"**
4. Fill in:
   - **Name**: Form name
   - **Kobo ID**: Unique identifier
   - **Version**: Form version
   - **XML Content**: Paste XForm XML
   - **OR XLSForm File**: Upload XLSForm file (auto-converts to XML)
5. Click **"Save"**

#### Method 2: Using API

```python
import requests

url = "http://localhost:8000/api/forms/"
data = {
    "name": "Survey Form",
    "kobo_id": "survey_001",
    "xml_content": """<?xml version="1.0"?>
    <h:html xmlns:h="http://www.w3.org/1999/xhtml" xmlns="http://www.w3.org/2002/xforms">
      <!-- Your XForm XML here -->
    </h:html>""",
    "version": "1.0"
}

response = requests.post(url, json=data)
print(response.json())
```

#### Method 3: Using cURL

```bash
curl -X POST http://localhost:8000/api/forms/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Survey Form",
    "kobo_id": "survey_001",
    "xml_content": "<?xml version=\"1.0\"?>...",
    "version": "1.0"
  }'
```

### Submitting Form Data

#### Method 1: Using Enketo (Recommended)

1. Go to `http://localhost:8000/forms/`
2. Click on a form
3. Click **"Fill New Form"**
4. Fill out the form in Enketo
5. Submit the form
6. Data is automatically saved to Django

#### Method 2: Using API

```python
import requests

url = "http://localhost:8000/api/submissions/submit/"
data = {
    "form_id": 1,
    "submission_data": {
        "name": "John Doe",
        "age": "30",
        "municipality": "Dili"
    },
    "status": "submitted"
}

response = requests.post(url, json=data)
print(response.json())
```

### Viewing Forms and Submissions

#### Using Web Interface

1. **View All Forms**: `http://localhost:8000/forms/`
2. **View Form Details**: `http://localhost:8000/forms/{id}/`
3. **View Submissions**: `http://localhost:8000/forms/{id}/` (shows submissions for that form)

#### Using API

```python
import requests

# Get all forms
response = requests.get("http://localhost:8000/api/forms/")
forms = response.json()
print(forms)

# Get form details
response = requests.get("http://localhost:8000/api/forms/1/")
form = response.json()
print(form)

# Get all submissions
response = requests.get("http://localhost:8000/api/submissions/")
submissions = response.json()
print(submissions)

# Filter submissions by form
response = requests.get("http://localhost:8000/api/submissions/?form=1")
filtered = response.json()
print(filtered)
```

### Using Django Admin

Django Admin provides a user-friendly interface:

1. **Access Admin**: `http://localhost:8000/admin/`
2. **Form Definitions**: Navigate to **API** → **Form definitions**
   - View all forms
   - Create new forms
   - Edit existing forms
   - Delete forms

3. **Form Submissions**: Navigate to **API** → **Form submissions**
   - View all submissions
   - Filter by form or status
   - Edit submissions
   - Delete submissions

### Using the Browsable API

Django REST Framework provides a browsable API:

1. **API Root**: `http://localhost:8000/api/`
   - Shows all available endpoints

2. **Forms List**: `http://localhost:8000/api/forms/`
   - View forms
   - Create new forms (requires authentication)
   - Filter and search

3. **Submissions List**: `http://localhost:8000/api/submissions/`
   - View submissions
   - Filter by form or status
   - Create submissions (requires authentication)

**Note:** To create/edit data through the browsable API, you need to log in first.

---

## Workflows

### Complete Workflow: Import Form → Fill Form → View Submission

#### Step 1: Import Form from Kobo

**Option A: Using Kobo API Integration**

1. Go to `http://localhost:8000/kobo/import/`
2. Click **"Import Form"** for the form you want
3. Form is imported into Django

**Option B: Using Django Admin**

1. Get XForm XML from Kobo
2. Go to Django Admin → **API** → **Form definitions**
3. Create new form definition
4. Paste XML or upload XLSForm file
5. Save

#### Step 2: Fill Out Form

1. Go to `http://localhost:8000/forms/`
2. Click on the form you want to fill
3. Click **"Fill New Form"**
4. Enketo opens with the form
5. Fill out the form
6. Submit the form
7. You're redirected back to Django with a success message

#### Step 3: View Submission

1. Go to `http://localhost:8000/forms/{form_id}/`
2. See all submissions for that form
3. Click on a submission to view details
4. Edit submission if needed

### Workflow: Import Existing Submissions from Kobo

1. Import form from Kobo (see above)
2. Go to `http://localhost:8000/kobo/import/`
3. Find your imported form
4. Click **"Import Submissions"**
5. All submissions from Kobo are imported into Django
6. View submissions at `http://localhost:8000/forms/{form_id}/`

### Workflow: Edit Existing Submission

1. Go to `http://localhost:8000/forms/{form_id}/`
2. Click on a submission
3. Click **"Edit Submission"**
4. Enketo opens with pre-filled data
5. Edit the form
6. Submit changes
7. Updated submission is saved

---

## Services

### EnketoService

Service for interacting with Enketo Express API.

**Location:** `api/services/enketo_service.py`

**Methods:**

- `render_form(form_xml, instance_id=None)`: Render a form using Enketo Express
- `get_submission(submission_id)`: Retrieve submission data from Enketo

**Usage:**
```python
from api.services import EnketoService

service = EnketoService()

# Render a form
form = FormDefinition.objects.get(id=1)
result = service.render_form(form.xml_content)
enketo_url = result.get('url')

# Get submission
submission_data = service.get_submission(submission_id)
```

### KoboService

Service for interacting with Kobo Toolbox API.

**Location:** `api/services/kobo_service.py`

**Methods:**

- `get_forms()`: Get list of forms from Kobo
- `get_form_xml(asset_id)`: Get form XML from Kobo
- `get_submissions(asset_id, limit=None)`: Get submissions from Kobo
- `import_form(asset_id, overwrite=False)`: Import form from Kobo

**Usage:**
```python
from api.services import KoboService

service = KoboService()

# Get all forms
forms = service.get_forms()

# Get form XML
xml = service.get_form_xml('asset_id_here')

# Import form
form = service.import_form('asset_id_here', overwrite=False)
```

---

## Troubleshooting

### Django Configuration Issues

#### Error: "Enketo Not Configured"

**Solution:**
1. Check `ENKETO_URL` is set in `.env` file
2. Restart Django server after changing `.env`
3. Verify Enketo Express is running

#### Error: "Environment Variables Not Loading"

**Solution:**
1. Make sure `.env` file is in correct location: `django_api_enpoint/.env`
2. Check `python-dotenv` is installed: `pip install python-dotenv`
3. Restart Django server

#### Error: "Kobo Not Configured"

**Solution:**
1. Check `ACCESS_TOKEN` is set in `.env` file
2. Verify token is valid in Kobo Toolbox
3. Restart Django server

### API Issues

#### Error: "404 Not Found"

**Solution:**
- Check URL path is correct (should be `/api/forms/` not `/api/forms`)
- Verify server is running
- Check URL routing in `urls.py`

#### Error: "Permission Denied"

**Solution:**
- Check if authentication is required
- Verify user permissions
- Log in through Django Admin or API

#### Error: "Validation Error"

**Solution:**
- Check required fields are provided
- Verify data types match model requirements
- For FormDefinition: ensure `kobo_id` is unique

### Integration Issues

#### Error: "Enketo Connection Failed"

**Solution:**
1. Verify Enketo Express is running: `curl http://localhost:8005`
2. Check `ENKETO_URL` matches Enketo port
3. Verify `ENKETO_API_TOKEN` matches Enketo config
4. Check network connectivity

#### Error: "Form Rendering Failed"

**Solution:**
1. Verify form XML is valid
2. Check Enketo logs for errors
3. Verify form exists in database
4. Check Enketo service is accessible

#### Error: "Kobo API Error"

**Solution:**
1. Verify `ACCESS_TOKEN` is correct
2. Check internet connection
3. Verify asset ID is correct
4. Check Kobo API status

### Database Issues

#### Error: "Form Not Found"

**Solution:**
- Verify form exists: Check Django Admin
- Verify form ID is correct
- Check form is active (`is_active=True`)

#### Error: "Submission Not Found"

**Solution:**
- Verify submission exists: Check Django Admin
- Verify submission ID is correct
- Check submission belongs to the form

### Common Solutions

#### Restart Services

```bash
# Restart Django
python manage.py runserver

# Restart Enketo (if using pm2)
pm2 restart enketo

# Or restart Enketo manually (from monorepo root)
cd enketo
nvm use 20
yarn workspace enketo-express start

# Or from package directory
cd enketo/packages/enketo-express
nvm use 20
yarn start
```

#### Check Logs

```bash
# Django logs
# Check terminal where Django is running

# Enketo logs (if using pm2)
pm2 logs enketo

# Redis logs
redis-cli monitor
```

#### Verify Configuration

```bash
python manage.py shell
```

```python
from django.conf import settings
from api.services import EnketoService, KoboService

# Check Enketo
enketo = EnketoService()
print(f"Enketo enabled: {enketo.enabled}")
print(f"Enketo URL: {enketo.enketo_url}")

# Check Kobo
kobo = KoboService()
print(f"Kobo API URL: {kobo.api_base_url}")
print(f"Kobo token set: {bool(kobo.access_token)}")
```

---

## Summary

This integration provides:

- ✅ **Form Management**: Store and manage form definitions
- ✅ **Data Collection**: Collect submissions through Enketo
- ✅ **Kobo Integration**: Import forms and data from Kobo
- ✅ **API Access**: RESTful API for programmatic access
- ✅ **User Interface**: Web interface for managing forms

### Key Points

- Django stores forms and submissions
- Enketo Express renders forms for users
- Kobo Toolbox is the source for form definitions
- All three work together seamlessly

### Next Steps

1. Configure environment variables
2. Set up Enketo Express (see `ENKETO_AND_KOBO_GUIDE.md`)
3. Import forms from Kobo
4. Start collecting data!

