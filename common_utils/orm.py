from django.db.models import Q

ALWAYS_FALSE_Q = Q(pk__in=[])
"""Q условие, которое всегда будет ложным"""
