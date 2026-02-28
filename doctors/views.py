from django.db.models import F, Count
from django.shortcuts import render

from common_utils.decorators import sql_counter
from doctors.models import Doctor, Lpu, LpuSet


@sql_counter
def index(request):
    qs = Lpu.objects.filter(lpu_set__name='asd')
    print(qs)
    return render(request, 'doctors/index.html')
