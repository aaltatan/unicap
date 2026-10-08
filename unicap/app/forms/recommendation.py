from django import forms
from django.utils.translation import gettext_lazy as _

from unicap.domain import HireKind, RecommendationStrategy

from ..choices import HireKindChoices, RecommendationStrategyChoices


class RecommendationForm(forms.Form):
    """What the recommender may suggest, and which helping contract comes first."""

    strategy = forms.ChoiceField(
        label=_("strategy"),
        choices=RecommendationStrategyChoices.choices,
        initial=RecommendationStrategyChoices.FEWEST_CONTRACTS,
    )
    kinds = forms.MultipleChoiceField(
        label=_("contracts the university may sign"),
        choices=HireKindChoices.choices,
        initial=HireKindChoices.values,
        widget=forms.CheckboxSelectMultiple,
    )
    optimize_first = forms.BooleanField(
        label=_("optimize the current contracts first"),
        required=False,
        help_text=_("re-sign the current contracts first: new ones only fill what is left"),
    )

    def strategy_value(self) -> RecommendationStrategy:
        return RecommendationStrategy(self.cleaned_data["strategy"])

    def kinds_value(self) -> frozenset[HireKind]:
        return frozenset(HireKind(kind) for kind in self.cleaned_data["kinds"])
