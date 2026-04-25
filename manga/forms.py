from django import forms
from .models import Genre
class SearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label='Search',
        widget=forms.TextInput(attrs={
            'placeholder': 'Search manga title...',
            'autocomplete': 'off',
        }),
    )
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Any Status'),
            ('ongoing', 'Ongoing'),
            ('completed', 'Completed'),
            ('hiatus', 'Hiatus'),
            ('cancelled', 'Cancelled'),
        ],
    )
    manga_type = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Any Type'),
            ('ja', 'Manga'),
            ('ko', 'Manhwa'),
            ('zh', 'Manhua'),
        ],
    )
    sort = forms.ChoiceField(
        required=False,
        choices=[
            ('latest', 'Latest Update'),
            ('popular', 'Most Popular'),
            ('title', 'Title A-Z'),
            ('-title', 'Title Z-A'),
            ('year', 'Year'),
        ],
    )
    genres_include = forms.CharField(required=False, widget=forms.HiddenInput)
    genres_exclude = forms.CharField(required=False, widget=forms.HiddenInput)
    def clean_genres_include(self):
        raw = self.cleaned_data.get('genres_include', '')
        return [g.strip() for g in raw.split(',') if g.strip()]
    def clean_genres_exclude(self):
        raw = self.cleaned_data.get('genres_exclude', '')
        return [g.strip() for g in raw.split(',') if g.strip()]
