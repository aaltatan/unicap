from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import Chapter


class ChapterForm(forms.ModelForm):
    class Meta:
        model = Chapter
        fields = (
            "name",
            "max_students",
            "notes",
        )
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": _("e.g. 2026 / Fall"), "autofocus": True}
            ),
            "notes": forms.Textarea(attrs={"rows": 2, "x-autosize": ""}),
        }


class DuplicateChapterForm(forms.Form):
    name = forms.CharField(
        label=_("name of the copy"),
        max_length=255,
        widget=forms.TextInput(attrs={"autofocus": True}),
    )

    def clean_name(self) -> str:
        name = self.cleaned_data["name"].strip()

        if Chapter.objects.filter(name=name).exists():
            raise forms.ValidationError(_("a chapter with this name already exists."))

        return name
