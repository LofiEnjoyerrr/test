from typing import Union, TypedDict

from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile

FILE_UPLOADED_TYPE = Union[InMemoryUploadedFile, TemporaryUploadedFile]


class AppointmentDirectionImageParams(TypedDict):
    size: tuple[int, int]
    quality: int
