from django.urls import path
from .views import *

app_name = 'medicine'

urlpatterns = [
    path('viewall', viewall, name='viewall'),
    path('create', create, name='create'),
    path('detail/<str:medicine_id>', detail, name='detail'),
    path('restock', restock, name='restock'),
    path('delete/<str:medicine_id>', delete, name='delete'),
]
