from rest_framework import serializers
from .models import Beneficiary, FormDefinition, FormSubmission, FormMedia


class BeneficiarySerializer(serializers.ModelSerializer):
    """Serializer for Beneficiary model."""
    
    class Meta:
        model = Beneficiary
        fields = '__all__'
        read_only_fields = ('id',)


class FormDefinitionSerializer(serializers.ModelSerializer):
    """Serializer for FormDefinition model."""
    
    submission_count = serializers.SerializerMethodField()
    
    class Meta:
        model = FormDefinition
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_submission_count(self, obj):
        """Get the count of submissions for this form."""
        return obj.formsubmission_set.count()
    
    def validate_xml_content(self, value):
        """Validate that XML content is provided."""
        if not value or not value.strip():
            raise serializers.ValidationError("XML content cannot be empty.")
        return value
    
    def validate_kobo_id(self, value):
        """Validate that kobo_id is unique."""
        if self.instance and self.instance.kobo_id == value:
            return value
        if FormDefinition.objects.filter(kobo_id=value).exists():
            raise serializers.ValidationError("A form with this Kobo ID already exists.")
        return value


class FormSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for FormSubmission model."""
    
    form_name = serializers.CharField(source='form.name', read_only=True)
    form_kobo_id = serializers.CharField(source='form.kobo_id', read_only=True)
    username = serializers.SerializerMethodField()
    
    class Meta:
        model = FormSubmission
        fields = '__all__'
        read_only_fields = ('id', 'submitted_at')
    
    def get_username(self, obj):
        """Safely get username, handling null user."""
        return obj.user.username if obj.user else None
    
    def validate_submission_data(self, value):
        """Validate that submission_data is a valid JSON object."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Submission data must be a valid JSON object.")
        if not value:
            raise serializers.ValidationError("Submission data cannot be empty.")
        return value
    
    def validate_status(self, value):
        """Validate status choice."""
        valid_statuses = [choice[0] for choice in FormSubmission._meta.get_field('status').choices]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(valid_statuses)}"
            )
        return value


class FormMediaSerializer(serializers.ModelSerializer):
    """Serializer for FormMedia model."""
    
    form_name = serializers.CharField(source='form.name', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = FormMedia
        fields = '__all__'
        read_only_fields = ('id', 'uploaded_at')
    
    def get_file_url(self, obj):
        """Get the full URL for the media file."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def validate_file(self, value):
        """Validate uploaded file."""
        if not value:
            raise serializers.ValidationError("File is required.")
        
        # Check file size (max 10MB by default)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size exceeds maximum allowed size of {max_size / (1024 * 1024)}MB."
            )
        
        return value
