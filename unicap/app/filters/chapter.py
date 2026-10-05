from django.utils.translation import gettext_lazy as _

from ..models import Chapter
from .base import BaseFilterSet, number_range


class ChapterFilter(BaseFilterSet):
    max_students_from, max_students_to = number_range("max_students", _("max students"))

    class Meta:
        model = Chapter
        fields = ("q",)
