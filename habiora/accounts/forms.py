from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import OwnerRequest, Profile, UserProfile


class RegisterForm(forms.ModelForm):

    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'})
    )
    password2 = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'})
    )
    role = forms.ChoiceField(
        choices=[('client', 'Client'), ('owner', 'Propriétaire')],
        initial='client',
        label="Je suis"
    )
    phone = forms.CharField(max_length=15, required=False, label="Téléphone")

    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name']

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("Cet email est déjà utilisé.")
        return email

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError("Les mots de passe ne correspondent pas.")
        if p1 and len(p1) < 8:
            raise ValidationError("Minimum 8 caractères.")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'phone_number': self.cleaned_data['phone'],
                    'role': 'proprietaire' if self.cleaned_data['role'] == 'owner' else 'client',
                },
            )
        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'autofocus': True, 'autocomplete': 'email'})
    )


class ProfileForm(forms.ModelForm):

    first_name = forms.CharField(max_length=50, required=False, label="Prénom")
    last_name = forms.CharField(max_length=50, required=False, label="Nom")
    phone = forms.CharField(max_length=20, required=False, label="Téléphone")

    class Meta:
        model = Profile
        fields = ['avatar', 'bio', 'birth_date', 'gender', 'location', 'website']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'maxlength': 500}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_id:
            u = self.instance.user
            self.fields['first_name'].initial = u.first_name
            self.fields['last_name'].initial = u.last_name
            profile = getattr(u, 'profile', None)
            self.fields['phone'].initial = profile.phone_number if profile else ''

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'size'):
            if avatar.size > 5 * 1024 * 1024:
                raise ValidationError("L'image ne doit pas dépasser 5 MB.")
        return avatar

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            profile.save()
            UserProfile.objects.update_or_create(
                user=user,
                defaults={'phone_number': self.cleaned_data['phone']},
            )
        return profile


class OwnerProfileForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = ['company_name', 'siret']

    def clean_siret(self):
        siret = self.cleaned_data.get('siret', '').strip()
        if siret and (len(siret) != 14 or not siret.isdigit()):
            raise ValidationError("Le SIRET doit contenir 14 chiffres.")
        return siret


class CustomPasswordChangeForm(PasswordChangeForm):

    def clean_new_password2(self):
        password = self.cleaned_data.get('new_password1')
        if password:
            if len(password) < 8:
                raise ValidationError("Minimum 8 caractères.")
            if not any(c.isupper() for c in password):
                raise ValidationError("Doit contenir une majuscule.")
            if not any(c.isdigit() for c in password):
                raise ValidationError("Doit contenir un chiffre.")
        return super().clean_new_password2()


class EmailChangeForm(forms.Form):

    new_email = forms.EmailField(label="Nouvel email")
    password = forms.CharField(widget=forms.PasswordInput, label="Mot de passe actuel")

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_email(self):
        email = self.cleaned_data['new_email'].lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("Cet email est déjà utilisé.")
        if email == self.user.email:
            raise ValidationError("C'est déjà votre email actuel.")
        return email

    def clean_password(self):
        password = self.cleaned_data['password']
        if not self.user.check_password(password):
            raise ValidationError("Mot de passe incorrect.")
        return password


class PreferencesForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = ['language', 'timezone', 'theme', 'email_notifications', 'push_notifications']


class DeleteAccountForm(forms.Form):

    password = forms.CharField(widget=forms.PasswordInput, label="Mot de passe")
    confirm = forms.BooleanField(
        required=True,
        label="Je confirme vouloir supprimer définitivement mon compte"
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        p = self.cleaned_data['password']
        if not self.user.check_password(p):
            raise ValidationError("Mot de passe incorrect.")
        return p

        # accounts/forms.py — AJOUTER

class OwnerRequestForm(forms.ModelForm):

    class Meta:
        model = OwnerRequest
        fields = [
            'company_name', 'siret', 'address', 'city',
            'postal_code', 'phone', 'message'
        ]
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_siret(self):
        siret = self.cleaned_data.get('siret', '').strip()
        if siret and (len(siret) != 14 or not siret.isdigit()):
            raise ValidationError("Le SIRET doit contenir exactement 14 chiffres.")
        return siret