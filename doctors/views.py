from django.db.models import F, Count, OuterRef, Exists, Prefetch
from django.shortcuts import render

from common_utils.decorators import sql_counter
from doctors.models import Doctor, Lpu, LpuSet, ServicePrice, WorkPlace


@sql_counter
def index(request):
    qs = Doctor.objects.all()
    list(qs)
    print(qs.exists())
    print(qs.exists())
    print(qs.exists())
    return render(request, 'doctors/index.html', )
