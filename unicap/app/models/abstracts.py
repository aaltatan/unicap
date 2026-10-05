from django.db import models
from django.utils.translation import gettext_lazy as _


class NotedModel(models.Model):
    """A row with free-text notes: for the people using the app, never part of a calculation."""

    notes = models.TextField(verbose_name=_("notes"), blank=True, default="")

    class Meta:
        abstract = True
