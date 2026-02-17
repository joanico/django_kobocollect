from django.db import models

class Beneficiary(models.Model):
    name = models.CharField(max_length=100, blank = True, null = True)
    date = models.DateTimeField(blank = True, null = True)
    municipality = models.CharField(max_length=100, blank = True, null = True)
    postadmin = models.CharField(max_length=100, blank = True, null = True)
    suco = models.CharField(max_length=100, blank = True, null = True)

    def __str__(self):
        return self.name


class Municipality(models.Model): 
    name = models.CharField(max_length=100, blank=True, null=True)

class PostAdmin(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    municipality = models.ForeignKey('Municipality', on_delete=models.CASCADE)

class Suco(models.Model):
    name = models.CharField(max_length=100, blank = True, null = True)
    postadmin = models.ForeignKey('PostAdmin', on_delete=models.CASCADE)

class FormDefinition(models.Model):
    """Stores Kobo form definition"""
    name  = models.CharField(max_length=200)
    kobo_id = models.CharField(max_length=100, unique=True)
    xml_content = models.TextField()
    version = models.CharField(max_length=100, default='1.0')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} (v{self.version})"
        
class FormSubmission(models.Model):
    """Store forms submission from Enketo"""
    form = models.ForeignKey('FormDefinition', on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True)
    submission_data = models.JSONField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=100, choices=[
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='submitted')
    
    class Meta:
        ordering = ['-submitted_at']
    
    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        return f"Submission #{self.id} - {self.form.name} by {user_str} ({self.status})"
    
class FormMedia(models.Model):
    """Store media files associated with forms"""
    form = models.ForeignKey('FormDefinition', on_delete=models.CASCADE)
    file = models.FileField(upload_to='form_media/')
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['form']
    
    def __str__(self):
        return f"{self.filename} - {self.form.name}"