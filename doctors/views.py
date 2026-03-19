from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models
from django.db.models import F, Count, OuterRef, Exists, Prefetch, Subquery, ExpressionWrapper, Q, Avg, Max
from django.db.models.functions import Coalesce
from django.shortcuts import render
from pygments.lexers import q

from common_utils.decorators import sql_counter
from doctors.models import Doctor, Lpu, LpuSet, ServicePrice, WorkPlace, Manipulation, DoctorMKBTypePractice
from doctors.serializers import IndexSerializer
from test import sync_manipulations_by_mkb


@sql_counter
def index(request):
    doctors_ids = [12]

    sync_manipulations_by_mkb(doctors_ids)

    return render(request, 'doctors/index.html', )
