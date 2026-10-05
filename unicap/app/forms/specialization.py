from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import Specialization
from .base import ChapterOwnedForm


class SpecializationForm(ChapterOwnedForm):
    class Meta:
        model = Specialization
        fields = ("name", "is_active", "notes")
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": _("e.g. Computer Science"), "autofocus": True}
            ),
            "notes": forms.Textarea(attrs={"rows": 2, "x-autosize": ""}),
        }

    def clean_name(self) -> str:
        name = self.cleaned_data["name"].strip()

        taken = Specialization.objects.filter(chapter=self.instance.chapter_id, name=name)

        if taken.exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(
                _("this chapter already has a specialization with this name.")
            )

        return name
