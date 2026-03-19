from collections import defaultdict
from typing import Iterable

from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.db.models import Prefetch, Q, Subquery, OuterRef, F, Value, IntegerField
from django.db.models.functions import Coalesce

from doctors.models import Doctor, Manipulation, DoctorMKBTypePractice


def sync_manipulations_by_mkb(doctors_ids: Iterable[int]):
    """
    Синхронизация автоматических манипуляций на основе выгруженных из МИС МКБ-10.
    Манипуляции подвязываются на мастеров.

    :param doctors_ids: ID врачей (как мастеров, так и слейвов), данные которых нужно синхронизировать.
    """
    doctors_to_sync = Doctor.objects.filter(
        Q(id__in=doctors_ids) | Q(doctor__id__in=doctors_ids),
        master__isnull=True,
    ).annotate(
        parsed_manipulations_types=Coalesce(
            Subquery(
                Manipulation.objects.filter(
                    is_parsed=True,
                    doctor_id=OuterRef('id'),
                )
                .values('doctor_id')
                .annotate(manipulations_types_ids=ArrayAgg('mtype_id', distinct=True))
                .values('manipulations_types_ids')
            ),
            Value([], output_field=ArrayField(IntegerField())),
        ),
        new_manipulations_types=Coalesce(
            Subquery(
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
            Value([], output_field=ArrayField(IntegerField())),
        )
    ).distinct()

    manipulations_to_create = []
    for doctor in doctors_to_sync:
        new_manipulations_types_ids = set(doctor.new_manipulations_types)
        existing_manipulations_types_ids = set(doctor.parsed_manipulations_types)
        manipulations_types_ids_to_delete = existing_manipulations_types_ids - new_manipulations_types_ids

        Manipulation.objects.filter(
            doctor=doctor,
            is_parsed=True,
            mtype_id__in=manipulations_types_ids_to_delete,
        ).delete()

        manipulations_to_create.extend(
            [
                Manipulation(
                    doctor=doctor,
                    mtype_id=mtype_id,
                    frequency=0,  # У автоматических манипуляций это поле не используется
                    is_parsed=True,
                )
                for mtype_id in new_manipulations_types_ids
            ],
        )

    Manipulation.objects.bulk_create(
        manipulations_to_create,
        batch_size=100,
        ignore_conflicts=True,
    )

