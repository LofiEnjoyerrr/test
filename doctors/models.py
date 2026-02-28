from django.db import models

from common_utils.mixins import AutoDateMixin


class Doctor(AutoDateMixin):
    """Модель: Врач"""

    surname = models.CharField(max_length=100, verbose_name='Фамилия')
    firstname = models.CharField(max_length=100, verbose_name='Имя')
    patronymic = models.CharField(max_length=100, verbose_name='Отчество')
    age = models.PositiveSmallIntegerField(verbose_name='Возраст')

    class Meta:
        """Мета-класс"""

        verbose_name = 'Врач'
        verbose_name_plural = 'Врачи'

    def __str__(self) -> str:
        """Строковое представление объекта"""
        return f'Врач ({self.surname} {self.firstname} {self.patronymic})'


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
