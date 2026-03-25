from django.urls import path

from doctors.views import index, AjaxAPIView

urlpatterns = [
    path('', index),
    path('ajax/', AjaxAPIView.as_view()),
]
