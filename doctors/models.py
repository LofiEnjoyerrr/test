import os
from io import BytesIO

from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import UniqueConstraint

from common_utils.mixins import AutoDateMixin
from doctors.types import FILE_UPLOADED_TYPE, AppointmentDirectionImageParams


def get_service_appointment_direction_filepath(instance: 'AppointmentDirection', filename: str) -> str:
    direction_path = f'photo/appointments_directions/appointment_{instance.appointment_id}/direction.jpg'
    private_direction_path = os.path.join('private/', direction_path)
    return private_direction_path


class Doctor(AutoDateMixin):
    """Модель: Врач"""

    surname = models.CharField(max_length=100, verbose_name='Фамилия')
    firstname = models.CharField(max_length=100, verbose_name='Имя')
    patronymic = models.CharField(max_length=100, verbose_name='Отчество')
    age = models.PositiveSmallIntegerField(verbose_name='Возраст')
    master = models.ForeignKey(
        'doctors.Doctor',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name='Мастер врача',
    )

    class Meta:
        """Мета-класс"""

        verbose_name = 'Врач'
        verbose_name_plural = 'Врачи'

    def __str__(self) -> str:
        """Строковое представление объекта"""
        return f'Врач (#{self.id}) ({self.surname} {self.firstname} {self.patronymic})'


class Lpu(AutoDateMixin):
    """Модель: ЛПУ"""

    name = models.CharField(max_length=300, verbose_name='Название')
    lpu_set = models.ForeignKey(
        'doctors.LpuSet',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Сеть ЛПУ',
    )
    services = models.ManyToManyField('doctors.Service', through='doctors.ServicePrice', verbose_name='Услуги')

    class Meta:
        """Мета-класс"""

        verbose_name = 'ЛПУ'
        verbose_name_plural = 'ЛПУ'

    def __str__(self) -> str:
        """Строковое представление объекта"""
        return f'ЛПУ {self.name}'


class LpuSet(AutoDateMixin):
    """Модель: Сеть ЛПУ"""

    name = models.CharField(max_length=300, verbose_name='Название')

    class Meta:
        """Мета-класс"""

        verbose_name = 'Сеть ЛПУ'
        verbose_name_plural = 'Сети ЛПУ'

    def __str__(self) -> str:
        """Строковое представление объекта"""
        return f'Сеть ЛПУ {self.name}'


class LpuInformation(AutoDateMixin):
    """Модель: Информацию о ЛПУ"""

    lpu = models.OneToOneField(Lpu, on_delete=models.CASCADE, verbose_name='ЛПУ')

    has_parking = models.BooleanField(db_default=False, verbose_name='Есть парковка')
    has_pandus = models.BooleanField(db_default=False, verbose_name='Есть пандус')

    class Meta:
        """Мета-класс"""

        verbose_name = 'Информация о ЛПУ'
        verbose_name_plural = 'Информации о ЛПУ'

    def __str__(self) -> str:
        """Строковое представление объекта"""
        return f'Информация о ЛПУ (#{self.lpu_id})'


class WorkPlace(AutoDateMixin):
    """Модель: Место работы врача"""

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, verbose_name='Врач')
    lpu = models.ForeignKey(Lpu, on_delete=models.CASCADE, verbose_name='ЛПУ')

    online_appointment_on = models.BooleanField(db_default=False, verbose_name='Включена онлайн-запись')

    class Meta:
        """Мета-класс"""

        verbose_name = 'Место работы врача'
        verbose_name_plural = 'Места работы врачей'

    def __str__(self) -> str:
        """Строковое представление объекта"""
        return f'Место работы врача (#{self.doctor_id}) в ЛПУ (#{self.lpu_id})'


class Service(AutoDateMixin):
    """Модель: Услуга"""

    name = models.CharField(max_length=300, verbose_name='Название')

    class Meta:
        """Мета-класс"""

        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'

    def __str__(self) -> str:
        """Строковое представление объекта"""
        return f'Услуга {self.name}'


class ServicePrice(AutoDateMixin):
    """Модель: Услуга в ЛПУ"""

    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name='Услуга')
    lpu = models.ForeignKey(Lpu, on_delete=models.CASCADE, verbose_name='ЛПУ')

    price = models.PositiveIntegerField(verbose_name='Цена услуги')

    class Meta:
        """Мета-класс"""

        verbose_name = 'Услуга в ЛПУ'
        verbose_name_plural = 'Услуги в ЛПУ'

    def __str__(self) -> str:
        """Строковое представление объекта"""
        return f'Услуга (#{self.service_id}) в ЛПУ (#{self.lpu_id})'


class Appointment(AutoDateMixin):
    """Модель: Запись на приём"""

    workplace = models.ForeignKey('doctors.WorkPlace', on_delete=models.PROTECT, verbose_name='Место работы')

    class Meta:
        """Мета-класс"""

        verbose_name = 'Запись на приём'
        verbose_name_plural = 'Записи на приём'

    def __str__(self) -> str:
        """Строковое представление объекта"""
        return f'Запись на приём (#{self.id}) по месту работы (#{self.workplace_id})'


class ManipulationType(AutoDateMixin):
    """Модель: Тип манипуляции"""

    name = models.CharField(unique=True, verbose_name='Название типа')

    class Meta:
        """Мета-класс"""

        verbose_name = 'Тип манипуляции'
        verbose_name_plural = 'Типы манипуляции'

    def __str__(self) -> str:
        """Строковое представление объекта"""
        return f'Тип манипуляции (#{self.id}) \'{self.name}\''


class Manipulation(AutoDateMixin):
    """Модель: Манипуляция врача"""

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, verbose_name='Доктор')
    mtype = models.ForeignKey(ManipulationType, on_delete=models.CASCADE, verbose_name='Тип манипуляции')
    is_parsed = models.BooleanField(default=False, db_default=False, verbose_name='Автоматическая запись')
    is_active = models.BooleanField(default=True, db_default=True, verbose_name='Активность записи')
    frequency = models.IntegerField(null=True)

    class Meta:
        """Мета-класс"""

        verbose_name = 'Манипуляция врача'
        verbose_name_plural = 'Манипуляции врачей'
        constraints = [
            UniqueConstraint(fields=['doctor', 'mtype'], name="unique_doctor_mtype")
        ]


    def __str__(self) -> str:
        """Строковое представление объекта"""
        return f'Манипуляция (#{self.id}) врача (#{self.doctor_id})'


class MKBType(AutoDateMixin):
    """Модель: Болезнь по МКБ-10"""

    code = models.CharField(unique=True, verbose_name='Код болезни')
    manipulation_types = models.ManyToManyField(ManipulationType)

    class Meta:
        """Мета-класс"""

        verbose_name = 'Болезнь по МКБ-10'
        verbose_name_plural = 'Болезни по МКБ-10'

    def __str__(self) -> str:
        """Строковое представление объекта"""
        return f'Болезнь по МКБ-10 (#{self.id}) (#{self.code})'


class DoctorMKBTypePractice(AutoDateMixin):
    """Модель: Практика врача по МКБ"""

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, verbose_name='Доктор')
    mkb_type = models.ForeignKey(MKBType, on_delete=models.CASCADE, verbose_name='МКБ-болезнь')
    total_appointments = models.PositiveIntegerField(default=0, db_default=0, verbose_name='Число приёмов')

    class Meta:
        """Мета-класс"""

        verbose_name = 'Практика врача по МКБ'
        verbose_name_plural = 'Практики врача по МКБ'

    def __str__(self) -> str:
        """Строковое представление объекта"""
        return f'Практика врача (#{self.id}) по МКБ (#{self.mkb_type.code})'


class DoctorPractice(AutoDateMixin):
    """Модель: Практика врача"""

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, verbose_name='Доктор')

    total_appointments = models.PositiveIntegerField(verbose_name='Общее число приёмов')

    class Meta:
        """Мета-класс"""

        verbose_name = 'Практика врача'
        verbose_name_plural = 'Практики врачей'

    def __str__(self) -> str:
        """Строковое представление объекта"""
        return f'Практика (#{self.id}) врача (#{self.doctor_id})'


class AppointmentDirection(AutoDateMixin):
    """Модель: Направление на услугу"""

    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, verbose_name='Запись к врачу')
    processed_image = models.ImageField(
        max_length=200,
        blank=True,
        default='',
        validators=[FileExtensionValidator(allowed_extensions=('jpeg', 'jpg', 'png', 'heic'))],
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
        new_size = processed_direction_params['size']
        new_quality = processed_direction_params['quality']

        if direction_image.mode != 'RGB':
            direction_image = direction_image.convert('RGB')

        direction_image.thumbnail(new_size, Image.Resampling.LANCZOS)

        output = BytesIO()

        direction_image.save(output, quality=new_quality, format='JPEG')
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
