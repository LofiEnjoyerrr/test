from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models
from django.db.models import F, Count, OuterRef, Exists, Prefetch, Subquery, ExpressionWrapper, Q, Avg, Max
from django.shortcuts import render
from pygments.lexers import q

from common_utils.decorators import sql_counter
from doctors.models import Doctor, Lpu, LpuSet, ServicePrice, WorkPlace


@sql_counter
def index(request):
    qs = (
        Lpu.objects
        .values('id')
        .annotate(cnt=Count('workplace__'))
        .values('id', 'name', 'workplace__doctor', 'cnt')
    )
    list(qs)
    print(qs)

    return render(request, 'doctors/index.html', )
