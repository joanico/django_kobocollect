# Enketo Express Integration Design Document
## Django + Kobo Collect Integration

### 1. Executive Summary

This document outlines the design for integrating Enketo Express (the web form engine used by Kobo Collect) with the existing Django project. The integration will enable web-based form rendering, data collection, and seamless integration with the current Kobo API data flow.

### 2. Current System Analysis

#### 2.1 Existing Architecture
- **Django 3.2.8** application with PostgreSQL database
- **API app** handling Kobo data with models for Beneficiary, Municipality, PostAdmin, and Suco
- **Current data flow**: Kobo API → Django → Database storage
- **Static file serving** and template-based rendering

#### 2.2 Current Limitations
- No web-based form interface for data entry
- Limited user interaction beyond API consumption
- No offline-capable form rendering
- Manual data entry through Django admin only

### 3. Integration Architecture

#### 3.1 High-Level Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Kobo API     │    │   Django Backend │    │  Enketo Express │
│                 │    │                  │    │                 │
│ • Form XML      │───▶│ • Form Storage   │───▶│ • Form Rendering│
│ • Data Export   │    │ • User Auth      │    │ • Data Entry    │
│ • Media Files   │    │ • Data Processing│    │ • Validation    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  PostgreSQL DB  │    │  Form Submissions│
                       │                  │    │                 │
                       │ • Form Metadata │    │ • Response Data │
                       │ • User Data     │    │ • Media Files   │
                       │ • Submissions   │    │ • Audit Trail   │
                       └──────────────────┘    └─────────────────┘
```

#### 3.2 Component Responsibilities

**Django Backend:**
- Form management and storage
- User authentication and authorization
- Data processing and validation
- API endpoints for Enketo integration
- File upload handling

**Enketo Express:**
- XForm rendering and display
- Client-side form validation
- Offline data collection
- Media file handling
- Form submission

### 4. Technical Implementation

#### 4.1 New Django Models

```python
# api/models.py additions

class FormDefinition(models.Model):
    """Stores Kobo form definitions"""
    name = models.CharField(max_length=200)
    kobo_id = models.CharField(max_length=100, unique=True)
    xml_content = models.TextField()
    version = models.CharField(max_length=20, default='1.0')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']

class FormSubmission(models.Model):
    """Stores form submissions from Enketo"""
    form = models.ForeignKey(FormDefinition, on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True)
    submission_data = models.JSONField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('validated', 'Validated'),
        ('rejected', 'Rejected')
    ], default='submitted')
    
    class Meta:
        ordering = ['-submitted_at']

class FormMedia(models.Model):
    """Stores media files associated with forms"""
    form = models.ForeignKey(FormDefinition, on_delete=models.CASCADE)
    file = models.FileField(upload_to='form_media/')
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
```

#### 4.2 New Django Apps

**`enketo` app:**
- Form management views and APIs
- Enketo integration services
- Form submission handling

**`forms` app:**
- Form definition management
- Form builder interface
- Form validation logic

#### 4.3 API Endpoints

```python
# api/urls.py additions

from django.urls import path
from . import views

urlpatterns = [
    # Existing endpoints...
    path('forms/', views.FormListView.as_view(), name='form-list'),
    path('forms/<int:pk>/', views.FormDetailView.as_view(), name='form-detail'),
    path('forms/<int:pk>/render/', views.FormRenderView.as_view(), name='form-render'),
    path('forms/<int:pk>/submit/', views.FormSubmitView.as_view(), name='form-submit'),
    path('submissions/', views.SubmissionListView.as_view(), name='submission-list'),
    path('submissions/<int:pk>/', views.SubmissionDetailView.as_view(), name='submission-detail'),
]
```

#### 4.4 Enketo Integration Service

```python
# api/services/enketo_service.py

import requests
from django.conf import settings
import json

class EnketoService:
    def __init__(self):
        self.enketo_url = settings.ENKETO_URL
        self.api_token = settings.ENKETO_API_TOKEN
    
    def render_form(self, form_xml, instance_id=None):
        """Render a form using Enketo Express"""
        payload = {
            'form': form_xml,
            'instance_id': instance_id,
            'return_url': f"{settings.SITE_URL}/forms/submit/"
        }
        
        headers = {
            'Authorization': f'Token {self.api_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f"{self.enketo_url}/api/v2/survey",
            json=payload,
            headers=headers
        )
        
        return response.json()
    
    def get_submission(self, submission_id):
        """Retrieve submission data from Enketo"""
        headers = {
            'Authorization': f'Token {self.api_token}'
        }
        
        response = requests.get(
            f"{self.enketo_url}/api/v2/survey/{submission_id}",
            headers=headers
        )
        
        return response.json()
```

### 5. Frontend Integration

#### 5.1 Enketo Express Setup

**Option 1: Self-hosted Enketo Express**
- Deploy Enketo Express as a separate service
- Configure CORS and authentication
- Customize themes and branding

**Option 2: Enketo Cloud (SaaS)**
- Use Enketo's hosted service
- Configure API keys and webhooks
- Limited customization but easier maintenance

#### 5.2 Django Template Integration

```html
<!-- templates/api/form_render.html -->
{% extends 'base.html' %}

{% block content %}
<div class="form-container">
    <div class="form-header">
        <h2>{{ form.name }}</h2>
        <p>Version: {{ form.version }}</p>
    </div>
    
    <div id="enketo-form" class="enketo-container">
        <!-- Enketo form will be embedded here -->
    </div>
    
    <div class="form-actions">
        <button id="save-draft" class="btn btn-secondary">Save Draft</button>
        <button id="submit-form" class="btn btn-primary">Submit Form</button>
    </div>
</div>

<script>
    // Enketo integration JavaScript
    const formData = {
        formId: '{{ form.kobo_id }}',
        enketoUrl: '{{ enketo_url }}',
        submissionUrl: '{% url "form-submit" form.pk %}'
    };
    
    // Initialize Enketo form
    initializeEnketoForm(formData);
</script>
{% endblock %}
```

### 6. Data Flow and Synchronization

#### 6.1 Form Lifecycle

1. **Form Creation**: Kobo form XML imported via management command
2. **Form Storage**: XML stored in Django database with metadata
3. **Form Rendering**: Enketo Express renders form from stored XML
4. **Data Collection**: Users fill out forms (online/offline)
5. **Form Submission**: Data submitted to Django backend
6. **Data Processing**: Validation, transformation, and storage
7. **Sync with Kobo**: Processed data sent back to Kobo if needed

#### 6.2 Offline Support

- **Service Worker**: Cache form definitions and submissions
- **IndexedDB**: Local storage for offline data
- **Sync Queue**: Queue submissions when offline
- **Conflict Resolution**: Handle data conflicts on reconnection

### 7. Security and Authentication

#### 7.1 Authentication Strategy

- **JWT Tokens**: For API authentication
- **Session-based**: For web interface
- **OAuth2**: Integration with Kobo accounts
- **Role-based Access**: Different permissions for different user types

#### 7.2 Data Security

- **HTTPS Only**: All communications encrypted
- **Input Validation**: Server-side validation of all submissions
- **CSRF Protection**: Cross-site request forgery prevention
- **File Upload Security**: Validate and sanitize uploaded files

### 8. Performance and Scalability

#### 8.1 Caching Strategy

- **Redis**: Cache form definitions and user sessions
- **CDN**: Static assets and media files
- **Database Indexing**: Optimize queries on form submissions
- **Lazy Loading**: Load form components as needed

#### 8.2 Scalability Considerations

- **Horizontal Scaling**: Multiple Django instances
- **Load Balancing**: Distribute traffic across servers
- **Database Sharding**: Partition data by form or user
- **Async Processing**: Background tasks for heavy operations

### 9. Deployment and Infrastructure

#### 9.1 Docker Configuration

```dockerfile
# Dockerfile.enketo
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 8005
CMD ["npm", "start"]
```

```yaml
# docker-compose.yml additions
  enketo:
    build:
      context: ./enketo
      dockerfile: Dockerfile.enketo
    ports:
      - "8005:8005"
    environment:
      - NODE_ENV=production
      - ENKETO_API_KEY=${ENKETO_API_KEY}
    volumes:
      - enketo_data:/app/data
    depends_on:
      - redis
```

#### 9.2 Environment Configuration

```python
# settings.py additions

# Enketo Configuration
ENKETO_URL = os.getenv('ENKETO_URL', 'http://localhost:8005')
ENKETO_API_TOKEN = os.getenv('ENKETO_API_TOKEN')
ENKETO_WEBFORM_URL = os.getenv('ENKETO_WEBFORM_URL', 'http://localhost:8005')

# Form Configuration
FORM_UPLOAD_DIR = os.path.join(BASE_DIR, 'media', 'forms')
MAX_FORM_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FORM_TYPES = ['xml', 'xlsx', 'csv']

# Redis Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
```

### 10. Testing Strategy

#### 10.1 Unit Tests

- Model validation and methods
- Service layer functionality
- API endpoint behavior
- Form processing logic

#### 10.2 Integration Tests

- End-to-end form submission
- Enketo API integration
- Database operations
- File upload handling

#### 10.3 Performance Tests

- Form rendering speed
- Submission processing time
- Concurrent user handling
- Database query performance

### 11. Implementation Plan

#### 11.1 Phase 1: Foundation (Weeks 1-2)

- Create new models and migrations
- Set up basic API endpoints
- Configure Enketo Express service
- Basic form storage and retrieval

#### 11.2 Phase 2: Core Integration (Weeks 3-4)

- Implement form rendering
- Add submission handling
- Basic offline support
- User authentication integration

#### 11.3 Phase 3: Advanced Features (Weeks 5-6)

- Advanced validation
- Media file handling
- Performance optimization
- Security hardening

#### 11.4 Phase 4: Testing and Deployment (Weeks 7-8)

- Comprehensive testing
- Production deployment
- Monitoring setup
- User training and documentation

### 12. Risk Assessment

#### 12.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|---------|------------|
| Enketo compatibility issues | Medium | High | Thorough testing, fallback options |
| Performance degradation | Medium | Medium | Load testing, caching strategy |
| Data loss during migration | Low | High | Comprehensive backups, dry runs |
| Security vulnerabilities | Low | High | Security audits, regular updates |

#### 12.2 Operational Risks

- **User Training**: Comprehensive documentation and training
- **Support**: Dedicated support team during transition
- **Communication**: Clear communication about changes
- **Timeline**: Buffer time for unexpected issues

### 13. Success Metrics

#### 13.1 Technical Metrics

- **Form Load Time**: < 3 seconds for 95% of users
- **Submission Success Rate**: > 99%
- **System Uptime**: > 99.9%
- **API Response Time**: < 500ms average

#### 13.2 Business Metrics

- **User Adoption**: > 80% of target users
- **Data Quality**: Reduced error rate by 50%
- **Efficiency**: 30% reduction in data entry time
- **Cost Savings**: 25% reduction in manual processing

### 14. Required Dependencies

```txt
# requirements.txt additions
djangorestframework==3.14.0
django-cors-headers==4.0.0
django-filter==23.0
celery==5.3.0
redis==4.5.0
psycopg2-binary==2.9.2
python-dotenv==0.19.0
requests==2.26.0
```

### 15. Conclusion

This integration will transform the current Django application from a simple data consumer to a comprehensive data collection and management platform. By leveraging Enketo Express, we'll provide users with a modern, responsive interface for data entry while maintaining the robust backend infrastructure.

The phased approach ensures minimal disruption to existing operations while building toward a more powerful and user-friendly system. The investment in this integration will pay dividends in improved data quality, user satisfaction, and operational efficiency.

### 16. Next Steps

1. **Review and Approval**: Stakeholder review of this design document
2. **Resource Allocation**: Assign development team and resources
3. **Environment Setup**: Prepare development and staging environments
4. **Development Kickoff**: Begin Phase 1 implementation
5. **Regular Reviews**: Weekly progress reviews and milestone tracking
