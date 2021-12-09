from rest_framework import serializers, generics
from .models import Beneficiary


class BeneficiarySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Beneficiary
        fields = '__all__'
