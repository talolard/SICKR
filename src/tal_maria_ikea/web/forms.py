"""Django forms for search and shortlist flows."""

from __future__ import annotations

from django import forms


class SearchForm(forms.Form):
    """Query and filter controls for semantic search."""

    query_text = forms.CharField(max_length=300, required=True)
    category = forms.CharField(max_length=120, required=False)

    min_price_eur = forms.FloatField(required=False, min_value=0)
    max_price_eur = forms.FloatField(required=False, min_value=0)

    width_exact_cm = forms.FloatField(required=False, min_value=0)
    width_min_cm = forms.FloatField(required=False, min_value=0)
    width_max_cm = forms.FloatField(required=False, min_value=0)

    depth_exact_cm = forms.FloatField(required=False, min_value=0)
    depth_min_cm = forms.FloatField(required=False, min_value=0)
    depth_max_cm = forms.FloatField(required=False, min_value=0)

    height_exact_cm = forms.FloatField(required=False, min_value=0)
    height_min_cm = forms.FloatField(required=False, min_value=0)
    height_max_cm = forms.FloatField(required=False, min_value=0)

    page = forms.IntegerField(required=False, min_value=1, initial=1)


class ShortlistNoteForm(forms.Form):
    """Optional note when adding shortlist items."""

    note = forms.CharField(max_length=300, required=False)
