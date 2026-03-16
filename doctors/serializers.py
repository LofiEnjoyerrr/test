from rest_framework import serializers

from doctors.models import Lpu


class IndexSerializer(serializers.Serializer):
    """Сериализатор index-вьюхи"""

    lpu = serializers.PrimaryKeyRelatedField(queryset=Lpu.objects.all())
