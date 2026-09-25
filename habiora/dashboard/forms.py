from django import forms
from .models import VerificationRequest


class ApproveForm(forms.Form):
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        label="Notes internes"
    )


class RejectForm(forms.Form):
    reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        label="Motif du rejet (visible par l'utilisateur)"
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        label="Notes internes (privées)"
    )
    
    def clean_reason(self):
        r = self.cleaned_data['reason'].strip()
        if len(r) < 10:
            raise forms.ValidationError("Le motif doit contenir au moins 10 caractères.")
        return r