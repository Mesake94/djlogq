from django.urls import path
from . import views

app_name = 'logq'

urlpatterns = [
    path('api/log/', views.log_endpoint, name='log_endpoint'),
    path('api/logs/', views.LogAPIView.as_view(), name='log_api'),
]