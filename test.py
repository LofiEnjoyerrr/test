from typing import Iterable

from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.db.models import *
from django.db.models.functions import Coalesce, RowNumber

from common_utils.orm import ALWAYS_FALSE_Q
from doctors.const import DOCTOR_PRACTICE_MIN_APPOINTMENTS
from doctors.models import *

def delete_doctors_practices_not_work_in_lpu(*, lpu_id: int, doctors_data: list[dict]):
    """
    Удаляем практики врачей, которые раньше работали в ЛПУ, но в новой выгрузке их не оказалось.

    :param lpu_id: ID ЛПУ
    :param doctors_data: Свежие данные по всем врачам в данном ЛПУ
    """
    new_doctors_ids = {doctor_data['doctor_id'] for doctor_data in doctors_data if doctor_data.get('doctor')}
    existing_doctors_ids = set(
        DoctorPractice.objects.filter(lpu_id=lpu_id).values_list(
            'doctor_id',
            flat=True,
        ),
    )
    doctors_ids_to_delete = existing_doctors_ids - new_doctors_ids

    DoctorPractice.objects.filter(lpu_id=lpu_id, doctor_id__in=doctors_ids_to_delete).delete()
    DoctorMKBTypePractice.objects.filter(lpu_id=lpu_id, doctor_id__in=doctors_ids_to_delete).delete()
    if FeatureFlags().use_mkb_with_manipulations:
        sync_manipulations_by_mkb(doctors_ids_to_delete)


def delete_doctors_practices_with_not_actual_mkb(*, lpu_id: int, doctors_data: list[dict]):
    """
    Удаляем неактуальные практики врачей по каким-то МКБ болезням.

    :param lpu_id: ID ЛПУ
    :param doctors_data: Свежие данные по всем врачам в данном ЛПУ
    """
    doctors_mkb_practice_to_delete_query = ALWAYS_FALSE_Q
    for doctor_data in doctors_data:
        # Для каждого доктора сравниваем перечень его текущих МКБ и новых
        doctor = doctor_data.get('doctor')
        if not doctor:
            continue

        new_doctor_mkb_type_codes = doctor_data['total_appointments_by_disease'].keys()
        existing_doctor_mkb_type_codes = {
            mkb_type_practice.mkb_type.code for mkb_type_practice in doctor.doctormkbtypepractice_set.all()
        }
        doctors_mkb_type_codes_to_delete = existing_doctor_mkb_type_codes - new_doctor_mkb_type_codes

        doctors_mkb_practice_to_delete_query |= Q(
            doctor_id=doctor.id,
            lpu_id=lpu_id,
            mkb_type__code__in=doctors_mkb_type_codes_to_delete,
        )
    DoctorMKBTypePractice.objects.filter(doctors_mkb_practice_to_delete_query).delete()


def update_or_create_doctors_practices(*, lpu_id: int, doctors_data: list[dict], mkb_id_by_code: dict):
    """
    Обновить объекты практик врачей

    :param lpu_id: ID ЛПУ
    :param doctors_data: Свежие данные по всем врачам в данном ЛПУ
    :param mkb_id_by_code: Перечень ID МКБ-болезней по их коду
    """
    batch_size = 2000

    # Обновляем DoctorPractice
    doctors_practices_to_create = (
        DoctorPractice(
            lpu_id=lpu_id,
            doctor_id=doctor_data['doctor_id'],
            total_appointments=doctor_data['total_appointments'],
            total_patients=doctor_data['total_patients'],
            total_patients_men=doctor_data['total_patients_men'],
            total_patients_women=doctor_data['total_patients_women'],
            **{
                pd_age_group: doctor_data['total_patients_by_age'].get(mf_age_group, 0)
                for mf_age_group, pd_age_group in DOCTOR_PRACTICE_AGE_FIELD_BY_MEDFLEX_ANNOTATION.items()
            },
        )
        for doctor_data in doctors_data
        if doctor_data.get('doctor')
    )
    while True:
        batch = list(islice(doctors_practices_to_create, batch_size))
        if not batch:
            break

        DoctorPractice.objects.bulk_create(
            batch,
            batch_size=batch_size,
            update_conflicts=True,
            update_fields=[
                'dt_updated',
                'total_appointments',
                'total_patients',
                'total_patients_men',
                'total_patients_women',
                *DOCTOR_PRACTICE_AGE_FIELD_BY_MEDFLEX_ANNOTATION.values(),
            ],
            unique_fields=['lpu_id', 'doctor_id'],
        )

    # Обновляем DoctorMKBTypePractice
    doctors_mkb_type_practices_to_create = (
        DoctorMKBTypePractice(
            lpu_id=lpu_id,
            doctor_id=doctor_data['doctor_id'],
            mkb_type_id=mkb_id,
            total_appointments=doctor_data['total_appointments_by_disease'].get(mkb_code, 0),
            total_patients=doctor_data['total_patients_by_disease'].get(mkb_code, 0),
        )
        for doctor_data in doctors_data
        if doctor_data.get('doctor')
        for mkb_code in doctor_data['total_appointments_by_disease']
        if (mkb_id := mkb_id_by_code.get(mkb_code))
    )
    while True:
        batch = list(islice(doctors_mkb_type_practices_to_create, batch_size))
        if not batch:
            break

        DoctorMKBTypePractice.objects.bulk_create(
            batch,
            batch_size=batch_size,
            update_conflicts=True,
            update_fields=[
                'dt_updated',
                'total_appointments',
                'total_patients',
            ],
            unique_fields=['lpu_id', 'doctor_id', 'mkb_type'],
        )


def validate_data_for_sync_doctors_practice(lpus_doctors_data: list[dict]):
    """
    Валидация данных на:
    1) Переданный ЛПУ существует
    2) Переданный доктор существует
    3) Переданный доктор работает в переданном ЛПУ

    Добавить к данным врачей, полученных из МИС, объекты врачей из БД.

    Если для ЛПУ, в котором работает слейв, был передан мастер - заменяем мастера на слейва.

    При получении невалидного ID врача, аннотируем None.

    Пример:
    >>> lpus_doctors_data = [{'doctors_statistics': [{'doctor_id': 1}, {'doctor_id': 123456789}]}]
    >>> validate_data_for_sync_doctors_practice(lpus_doctors_data)
    >>> [{'doctors_statistics': [{'doctor_id': 1, 'doctor': Doctor(1)}, {'doctor_id': 123456789, 'doctor': None}]}]

    :param lpus_doctors_data: Данные всех ЛПУ с данными их врачей
    """
    lpus_ids_to_retrieve = [lpu_data['lpu_id'] for lpu_data in lpus_doctors_data]
    lpu_objects_by_id = {
        lpu.id: lpu for lpu in Lpu.objects.filter(id__in=lpus_ids_to_retrieve).prefetch_related('workplace_set')
    }

    doctors_ids_to_retrieve = [
        doctor_data['doctor_id'] for lpu_data in lpus_doctors_data for doctor_data in lpu_data['doctors_statistics']
    ]
    doctor_objects_by_id = {
        doctor.id: doctor
        for doctor in Doctor.objects.filter(id__in=doctors_ids_to_retrieve).prefetch_related(
            'doctormkbtypepractice_set__mkb_type',
            'doctor_set',
        )
    }

    data_exception_was_captured = False
    for lpu_data in lpus_doctors_data:
        lpu_id = lpu_data['lpu_id']
        lpu = lpu_objects_by_id.get(lpu_id)
        if not lpu:
            data_exception_was_captured = True
            _logger.exception('Переданного ЛПУ (#%s) нет на ПД', lpu_id)
            continue

        for doctor_data in lpu_data['doctors_statistics']:
            doctor_id = doctor_data['doctor_id']
            doctor = doctor_objects_by_id.get(doctor_id)
            doctor_data['doctor'] = doctor
            if not doctor:
                data_exception_was_captured = True
                _logger.exception('Переданного врача (#%s) (ЛПУ %s) нет на ПД', doctor_id, lpu_id)
                continue

            for workplace in lpu.workplace_set.all():
                if workplace.doctor_id == doctor.id:
                    break
                if slave_doctor := next(
                    (slave for slave in doctor.doctor_set.all() if workplace.doctor_id == slave.id),
                    None,
                ):
                    doctor_data['doctor_id'] = slave_doctor.id
                    doctor_data['doctor'] = slave_doctor
                    break
            else:
                data_exception_was_captured = True
                doctor_data['doctor'] = None
                _logger.exception('В ЛПУ (#%s) не работает переданный врач (#%s)', lpu.pk, doctor.pk)

    if data_exception_was_captured:
        mattermost.post_to_channel(
            mattermost.ALERTS,
            'Новый профиль лечения. Из МФ пришли некорректные данные. Изучите логи и сообщите МФ.',
        )


def sync_doctors_practices(lpus_doctors_data: list[dict]):
    """
    Функция для синхронизации данных реальной практики врачей нескольких ЛПУ

    :param lpus_doctors_data: Данные, полученные из МИС
    """
    mkb_id_by_code = dict(MKBType.objects.values_list('code', 'id'))
    validate_data_for_sync_doctors_practice(lpus_doctors_data)

    for lpu_data in lpus_doctors_data:
        lpu_id = lpu_data['lpu_id']
        doctors_data = lpu_data['doctors_statistics']

        with transaction.atomic():
            delete_doctors_practices_not_work_in_lpu(lpu_id=lpu_id, doctors_data=doctors_data)
            delete_doctors_practices_with_not_actual_mkb(lpu_id=lpu_id, doctors_data=doctors_data)
            update_or_create_doctors_practices(lpu_id=lpu_id, doctors_data=doctors_data, mkb_id_by_code=mkb_id_by_code)

            if FeatureFlags().use_mkb_with_manipulations:
                doctors_ids = [doctor_data['doctor_id'] for doctor_data in doctors_data]
                sync_manipulations_by_mkb(doctors_ids)

    invalidate_doctors_practices_cache([lpu_data['lpu_id'] for lpu_data in lpus_doctors_data])


def invalidate_doctors_practices_cache(lpu_ids: Iterable[int]):
    """
    Инвалидировать кэш реальной лечебной практики всех врачей в переданных ЛПУ

    :param lpu_ids: ID множества ЛПУ
    """
    doctors_ids = (
        Doctor.objects.filter(
            workplace__lpu_id__in=lpu_ids,
        )
        .distinct()
        .values_list(Coalesce('master_id', 'id'), flat=True)
    )
    doctors_cache_keys = [DOCTOR_PRACTICE_CACHE_KEY.format(doctor_id) for doctor_id in doctors_ids]
    cache_interface.delete_many(keys=doctors_cache_keys)


def sync_manipulations_by_mkb(doctors_ids: Iterable[int]):
    """
    Синхронизация автоматических манипуляций на основе выгруженных из МИС МКБ-10.
    Манипуляции подвязываются на мастеров.

    :param doctors_ids: ID врачей (как мастеров, так и слейвов), данные которых нужно синхронизировать.
    """
    top_mkb_subquery = (
        DoctorMKBTypePractice.objects.filter(
            Q(doctor_id=OuterRef(OuterRef('id'))) |
            Q(doctor__master_id=OuterRef(OuterRef('id')))
        )
        .values('mkb_type_id')
        .annotate(total=Sum('total_appointments'))
        .order_by('-total')
        .values('mkb_type_id')[:10]
    )

    manipulations_subquery = (
        DoctorMKBTypePractice.objects.filter(
            Q(doctor_id=OuterRef('id')) |
            Q(doctor__master_id=OuterRef('id')),
            mkb_type__manipulation_types__isnull=False,
            mkb_type_id__in=top_mkb_subquery,
        )
        .annotate(master_doctor=Coalesce(F('doctor__master_id'), F('doctor_id')))
        .values('master_doctor')
        .annotate(
            manipulations_types_ids=ArrayAgg(
                'mkb_type__manipulation_types',
                distinct=True,
            )
        )
        .values('manipulations_types_ids')
    )

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
                Subquery(manipulations_subquery),
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
            activate_mkb_manipulations=Q(total_appointments__gte=DOCTOR_PRACTICE_MIN_APPOINTMENTS),
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
            active_manipulations_query |= Q(doctor=doctor, mtype_id__in=doctor.new_manipulations_types)
            inactive_manipulations_query |= Q(doctor=doctor) & ~Q(mtype_id__in=doctor.new_manipulations_types)
        # Просто включаем все ручные манипуляции, автоматические выключаем
        else:
            active_manipulations_query |= Q(doctor=doctor, is_parsed=False)
            inactive_manipulations_query |= Q(doctor=doctor, is_parsed=True)

    Manipulation.objects.filter(active_manipulations_query).update(is_active=True)
    Manipulation.objects.filter(inactive_manipulations_query).update(is_active=False)