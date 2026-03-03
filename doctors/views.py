from django.db.models import F, Count, OuterRef, Exists, Prefetch
from django.shortcuts import render

from common_utils.decorators import sql_counter
from doctors.models import Doctor, Lpu, LpuSet, ServicePrice, WorkPlace


@sql_counter
def index(request):
    qs = WorkPlace.objects.filter(doctor__firstname='Анна').select_related('doctor')

    list(qs)

    print(qs[0].doctor.patronymic)
    print(qs[0].doctor.patronymic)

    return render(request, 'doctors/index.html', )
