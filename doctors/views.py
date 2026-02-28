from django.shortcuts import render

from common_utils.decorators import sql_counter
from doctors.models import Doctor


@sql_counter
def index(request):
    doctors = Doctor.objects.filter(workplace__online_appointment_on=True).values('id')
    print(doctors)
    return render(request, 'doctors/index.html')
