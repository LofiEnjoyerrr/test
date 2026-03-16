from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models
from django.db.models import F, Count, OuterRef, Exists, Prefetch, Subquery, ExpressionWrapper, Q, Avg, Max
from django.shortcuts import render
from pygments.lexers import q

from common_utils.decorators import sql_counter
from doctors.models import Doctor, Lpu, LpuSet, ServicePrice, WorkPlace
from doctors.serializers import IndexSerializer


@sql_counter
def index(request):
    ser = IndexSerializer(data=request.GET)
    ser.is_valid(raise_exception=True)
    print(ser.validated_data)

    return render(request, 'doctors/index.html', )
