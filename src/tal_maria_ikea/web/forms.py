"""Django forms for search and shortlist flows."""

from __future__ import annotations

from django import forms


class SearchForm(forms.Form):
    """Query and filter controls for semantic search."""

    query_text = forms.CharField(max_length=300, required=True)
    category = forms.CharField(max_length=120, required=False)
    include_keyword = forms.CharField(max_length=120, required=False)
    exclude_keyword = forms.CharField(max_length=120, required=False)
    sort = forms.ChoiceField(
        choices=(
            ("relevance", "Relevance"),
            ("price_asc", "Price low-high"),
            ("price_desc", "Price high-low"),
            ("size", "Size"),
        ),
        required=False,
        initial="relevance",
    )

    min_price_eur = forms.FloatField(required=False, min_value=0)
    max_price_eur = forms.FloatField(required=False, min_value=0)

    exact_dimensions = forms.BooleanField(required=False)

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

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["query_text"].widget.attrs.update(
            {"placeholder": "e.g. large soft couch", "class": "input-text"}
        )
        self.fields["category"].widget.attrs.update(
            {"placeholder": "e.g. sofas-armchairs", "class": "input-text"}
        )
        self.fields["include_keyword"].widget.attrs.update(
            {"placeholder": "must include", "class": "input-text"}
        )
        self.fields["exclude_keyword"].widget.attrs.update(
            {"placeholder": "must exclude", "class": "input-text"}
        )
        self.fields["min_price_eur"].widget.attrs.update(
            {"placeholder": "min", "step": "0.01", "class": "input-number"}
        )
        self.fields["max_price_eur"].widget.attrs.update(
            {"placeholder": "max", "step": "0.01", "class": "input-number"}
        )
        for axis in ("width", "depth", "height"):
            self.fields[f"{axis}_min_cm"].widget.attrs.update(
                {"placeholder": "min", "step": "0.1", "class": "input-number"}
            )
            self.fields[f"{axis}_max_cm"].widget.attrs.update(
                {"placeholder": "max", "step": "0.1", "class": "input-number"}
            )
            self.fields[f"{axis}_exact_cm"].widget.attrs.update(
                {"placeholder": "exact", "step": "0.1", "class": "input-number"}
            )


class ShortlistNoteForm(forms.Form):
    """Optional note when adding shortlist items."""

    note = forms.CharField(max_length=300, required=False)
