from django.shortcuts import render

from common_utils.decorators import sql_counter
from doctors.models import Doctor


@sql_counter
def index(request):
    doctors = Doctor.objects.all()[:5]
    context = {'doctors': doctors}
    return render(request, 'doctors/index.html', context)
