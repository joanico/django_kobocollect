from django.urls import path
from . import views
from .views import GetKoboApi, api

urlpatterns = [
    path('', GetKoboApi.as_view(template_name="api/kobo_list.html"), name='koboapi'),
    path('response/', views.api, name='response'),
]
