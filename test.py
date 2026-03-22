from email.policy import default
from typing import Iterable

from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.db.models import Q, Subquery, OuterRef, F, Value, IntegerField, Count, When, Case
from django.db.models.aggregates import Sum
from django.db.models.functions import Coalesce

from common_utils.orm import ALWAYS_FALSE_Q
from doctors.models import Doctor, Manipulation, DoctorMKBTypePractice, DoctorPractice


def sync_manipulations_by_mkb(doctors_ids: Iterable[int]):
    """
    Синхронизация автоматических манипуляций на основе выгруженных из МИС МКБ-10.
    Манипуляции подвязываются на мастеров.

    :param doctors_ids: ID врачей (как мастеров, так и слейвов), данные которых нужно синхронизировать.
    """
    doctors_to_sync = (
        Doctor.objects.filter(
            Q(id__in=doctors_ids) | Q(doctor__id__in=doctors_ids),
            master__isnull=True,
        )
        .annotate(
            parsed_manipulations_types=Coalesce(
                Subquery(
                    Manipulation.objects.filter(
                        is_parsed=True,
                        doctor_id=OuterRef('id'),
                    )
                    .values('doctor_id')
                    .annotate(manipulations_types_ids=ArrayAgg('mtype_id', distinct=True))
                    .values('manipulations_types_ids'),
                ),
                Value([], output_field=ArrayField(IntegerField())),
            ),
            new_manipulations_types=Coalesce(
                Subquery(
                    DoctorMKBTypePractice.objects.filter(
                        Q(doctor_id=OuterRef('id')) | Q(doctor__master_id=OuterRef('id')),
                    )
                    .annotate(master_doctor=Coalesce(F('doctor__master_id'), F('doctor_id')))
                    .values('master_doctor')
                    .annotate(
                        manipulations_types_ids=ArrayAgg(
                            'mkb_type__manipulation_types',
                            distinct=True,
                        ),
                    )
                    .values('manipulations_types_ids'),
                ),
                Value([], output_field=ArrayField(IntegerField())),
            ),
            total_appointments=Coalesce(
                Subquery(
                    DoctorPractice.objects.filter(
                        Q(doctor_id=OuterRef('id')) | Q(doctor__master_id=OuterRef('id')),
                    )
                    .annotate(master_doctor=Coalesce(F('doctor__master_id'), F('doctor_id')))
                    .values('master_doctor')
                    .annotate(
                        total_appointments_sum=Sum('total_appointments'),
                    )
                    .values('total_appointments_sum'),
                ),
                0,
            ),
            activate_mkb_manipulations=Case(
                When(total_appointments__gte=100, then=True),
                default=False,
            )
        )
        .distinct()
    )

    # Удаляем устаревшие манипуляции и создаём новые
    manipulations_to_create = []
    manipulations_to_delete = ALWAYS_FALSE_Q
    for doctor in doctors_to_sync:
        new_manipulations_types_ids = set(doctor.new_manipulations_types)
        existing_manipulations_types_ids = set(doctor.parsed_manipulations_types)
        manipulations_types_ids_to_delete = existing_manipulations_types_ids - new_manipulations_types_ids

        manipulations_to_delete |= Q(
            doctor=doctor,
            is_parsed=True,
            mtype_id__in=manipulations_types_ids_to_delete,
        )

        manipulations_to_create.extend(
            [
                Manipulation(
                    doctor=doctor,
                    mtype_id=mtype_id,
                    frequency=0,  # У автоматических манипуляций это поле не используется
                    is_parsed=True,
                    is_active=False,
                )
                for mtype_id in new_manipulations_types_ids
            ],
        )

    Manipulation.objects.filter(manipulations_to_delete).delete()

    Manipulation.objects.bulk_create(
        manipulations_to_create,
        batch_size=100,
        ignore_conflicts=True,
    )

    # Обновляем активность манипуляций
    active_manipulations_query = ALWAYS_FALSE_Q
    inactive_manipulations_query = ALWAYS_FALSE_Q
    for doctor in doctors_to_sync:
        # Включаем все манипуляции (ручные и автоматические), у которых тип манипуляции совпадает с типом из МКБ
        if doctor.activate_mkb_manipulations:
            active_manipulations_query |= Q(
                doctor=doctor,
                mtype_id__in=doctor.new_manipulations_types,
            )
            inactive_manipulations_query |= (
                Q(doctor=doctor) & ~Q(mtype_id__in=doctor.new_manipulations_types)
            )
        # Просто включаем все ручные манипуляции, автоматические выключаем
        else:
            active_manipulations_query |= Q(
                doctor=doctor,
                is_parsed=False,
            )
            inactive_manipulations_query |= Q(
                doctor=doctor,
                is_parsed=True,
            )

    Manipulation.objects.filter(active_manipulations_query).update(is_active=True)
    Manipulation.objects.filter(inactive_manipulations_query).update(is_active=False)
