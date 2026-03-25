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
            activate_mkb_manipulations=Q(total_appointments__gte=100)
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


class AppointmentDirection(AutoDateMixin):
    """Модель: Направление на услугу"""

    processed_image = models.ImageField(
        max_length=IMAGE_MAX_LENGTH,
        blank=True,
        default='',
        validators=[FileExtensionValidator(allowed_extensions=('jpeg', 'jpg', 'png', 'heic', 'pdf'))],
        upload_to=get_service_appointment_direction_filepath,
        verbose_name='Обработанное изображение направления',
    )

    @classmethod
    def process_direction(cls, uploaded_file: FILE_UPLOADED_TYPE) -> ContentFile:
        """
        Сжать изображение направления.

        :param uploaded_file: Сжимаемый файл изображения направления на приём.

        :return: ContentFile с новым изображением
        """
        direction_image = Image.open(uploaded_file)
        # Поворот изображения, если имеется тэг EXIF у файла
        direction_image = ImageOps.exif_transpose(direction_image)

        processed_direction_params = cls._get_params_for_directon(direction_image)
        new_size = AppointmentDirectionImageParams['size']
        new_quality = AppointmentDirectionImageParams['quality']

        if direction_image.mode != 'RGB':
            direction_image = direction_image.convert('RGB')

        direction_image.thumbnail(new_size, Image.Resampling.LANCZOS)

        output = BytesIO()

        direction_image.save(output, quality=new_quality, format='JPEG', optimize=True)
        output.seek(0)

        base_name = os.path.splitext(uploaded_file.name)[0]
        new_name = f"{base_name}.jpg"

        return ContentFile(output.getvalue(), name=new_name)

    @classmethod
    def _get_params_for_directon(cls, uploaded_image: Image.Image) -> AppointmentDirectionImageParams:
        """
        Получить размеры (в пикселях) и качество для сжимаемого направления на приём.
        Мы сжимаем изображения направления по следующим правилам:
        · Если изображение по большей стороне меньше 500px, то размер изображения не изменяется, а степень сжатия 90
        · Если изображение по большей стороне меньше 1000px, то размер изображения не изменяется, а степень сжатия 80
        · Если изображение по большей стороне меньше 2000px, то размер изображения не изменяется, а степень сжатия 70
        · Если изображение по большей стороне больше 2000px, то размер изображения изменяется с сохранением пропорций
        до того размера, когда большая сторона будет равна 2000px. Степень сжатия 70.

        :param uploaded_image: Сжимаемый файл изображения направления на приём.

        :return: Размеры (в пикселях) и качество для сжимаемого направления на приём
        """
        width, height = uploaded_image.size
        biggest_size = max(width, height)
        if biggest_size < 500:
            return AppointmentDirectionImageParams(size=(width, height), quality=90)
        if biggest_size < 1000:
            return AppointmentDirectionImageParams(size=(width, height), quality=80)
        if biggest_size < 2000:
            return AppointmentDirectionImageParams(size=(width, height), quality=70)

        if width > height:
            new_height = int(height * (2000 / width))
            return AppointmentDirectionImageParams(size=(width, new_height), quality=70)
        new_width = int(width * (2000 / height))
        return AppointmentDirectionImageParams(size=(new_width, height), quality=70)
