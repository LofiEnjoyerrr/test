from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from doctors.const import MAX_APPOINTMENT_DIRECTION_SIZE, MAX_APPOINTMENT_DIRECTION_PIXEL_SIZE
from doctors.models import Lpu, AppointmentDirection


class IndexSerializer(serializers.ModelSerializer):
    """Сериализатор index-вьюхи"""

    class Meta:
        model = AppointmentDirection
        fields = '__all__'

    def validate_processed_image(self, image: InMemoryUploadedFile) -> ContentFile:
        if image.size > MAX_APPOINTMENT_DIRECTION_SIZE:
            raise ValidationError('Превышен максимальный размер файла: 16 МБ')
        width, height =  image.image.size
        if width * height > MAX_APPOINTMENT_DIRECTION_PIXEL_SIZE:
            raise ValidationError('Превышено максимальное разрешение файла: 4000x4000 px')
        return AppointmentDirection.process_direction(image)
