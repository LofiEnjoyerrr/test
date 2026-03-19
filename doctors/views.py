from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models
from django.db.models import F, Count, OuterRef, Exists, Prefetch, Subquery, ExpressionWrapper, Q, Avg, Max
from django.db.models.functions import Coalesce
from django.shortcuts import render
from pygments.lexers import q

from common_utils.decorators import sql_counter
from doctors.models import Doctor, Lpu, LpuSet, ServicePrice, WorkPlace, Manipulation, DoctorMKBTypePractice
from doctors.serializers import IndexSerializer


@sql_counter
def index(request):
    doctors_ids = []

    doctors_to_sync = Doctor.objects.filter(
        Q(id__in=doctors_ids) | Q(doctor__id__in=doctors_ids),
        master__isnull=True,
    ).annotate(
        parsed_manipulations_types=Subquery(
            Manipulation.objects.filter(
                is_parsed=True,
                doctor_id=OuterRef('id'),
            )
            .values('doctor_id')
            .annotate(manipulations_types_ids=ArrayAgg('mtype_id', distinct=True))
            .values('manipulations_types_ids')
        ),
        new_manipulations_types=Subquery(
            DoctorMKBTypePractice.objects.filter(
                Q(doctor_id=OuterRef('id'))
                | Q(doctor__master_id=OuterRef('id'))
            )
            .annotate(master_doctor=Coalesce(F('doctor__master_id'), F('doctor_id')))
            .values('master_doctor')
            .annotate(manipulations_types_ids=ArrayAgg(
                'mkb_type__manipulation_types',
                distinct=True,
            ))
            .values('manipulations_types_ids')
        ),
    ).distinct()

    print(doctors_to_sync)

    return render(request, 'doctors/index.html', )
