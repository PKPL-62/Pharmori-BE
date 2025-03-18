from django.urls import path
from .views import *

app_name = 'prescription'

urlpatterns = [
    path('viewall', viewall, name='viewall'),
    path('create', create, name='create'),
    path('detail/<str:prescription_id>', detail, name='detail'),
    path('delete/<str:prescription_id>', delete, name='delete'),
]
