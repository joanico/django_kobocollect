from django.urls import path
from . import views
from .views import GetKoboApi, ApiView

urlpatterns = [
    path('', GetKoboApi.as_view(template_name="api/kobo_list.html"), name='koboapi'),
    path('api/', ApiView.as_view(), name='api'),
]
