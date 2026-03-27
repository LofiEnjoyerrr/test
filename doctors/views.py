from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models
from django.db.models import F, Count, OuterRef, Exists, Prefetch, Subquery, ExpressionWrapper, Q, Avg, Max
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from pygments.lexers import q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common_utils.decorators import sql_counter
from doctors.models import Doctor, Lpu, LpuSet, ServicePrice, WorkPlace, Manipulation, DoctorMKBTypePractice
from doctors.serializers import IndexSerializer


@sql_counter
def index(request):
    d = Doctor.objects.filter(master__surname='asd').update(age=12)
    return render(request, 'doctors/index.html', )


class AjaxAPIView(APIView):

    def post(self, request, *args, **kwargs):
        serializer = IndexSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)