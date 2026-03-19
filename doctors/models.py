from django.db import models
from django.db.models import UniqueConstraint

from common_utils.mixins import AutoDateMixin


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

    class Meta:
        """Мета-класс"""

        verbose_name = 'Практика врача по МКБ'
        verbose_name_plural = 'Практики врача по МКБ'

    def __str__(self) -> str:
        """Строковое представление объекта"""
        return f'Практика врача (#{self.id}) по МКБ (#{self.mkb_type.code})'
