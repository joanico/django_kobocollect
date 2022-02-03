from django.urls import path
from . import views
from .views import GetKoboApi

urlpatterns = [
    path('', GetKoboApi,  name='aplikante'),
]
