from django.db import models


class AutoDateMixin(models.Model):
    """Модель: Миксин даты создания и обновления"""

    dt_created = models.DateTimeField(auto_now_add=True, verbose_name='Время создания')
    dt_updated = models.DateTimeField(auto_now=True, verbose_name='Время обновления')

    class Meta:
        """Мета-класс"""

        abstract = True
