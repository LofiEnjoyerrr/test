from django.urls import path

from doctors.views import index

urlpatterns = [
    path('', index),
]
