from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils import timezone
from .models import OwnerVerification
from notifications.models import Notification
import re 


def login_view(request):
    """Page de connexion avec l'adresse email."""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        email = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        
        if not email or not password:
            messages.error(request, "Veuillez remplir tous les champs.")
            return render(request, 'accounts/login.html')
        
        user = None
        try:
            user_obj = User.objects.get(email__iexact=email)
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            pass
        
        if user is not None:
            login(request, user)
            messages.success(request, f"Bonjour {user.username} !")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('home')
        else:
            messages.error(request, "Email ou mot de passe incorrect.")
    
    return render(request, 'accounts/login.html')


def register(request):
    """Page d'inscription"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        prenom = request.POST.get('prenom', '').strip()
        email = request.POST.get('email', '').strip()
        telephone = request.POST.get('telephone', '').strip()
        role = request.POST.get('role', 'client')
        password = request.POST.get('password')
        confirmation = request.POST.get('confirmation')
        conditions = request.POST.get('conditions')
        
        errors = []
        
        if not nom:
            errors.append("Le nom est obligatoire.")
        
        if not prenom:
            errors.append("Le prénom est obligatoire.")
        
        if not email:
            errors.append("L'email est obligatoire.")
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            errors.append("Veuillez entrer un email valide.")
        elif User.objects.filter(email=email).exists():
            errors.append("Cet email est déjà utilisé.")
        
        if not telephone:
            errors.append("Le numéro de téléphone est obligatoire.")
        elif not re.match(r'^[0-9+\s\-]{8,15}$', telephone):
            errors.append("Numéro de téléphone invalide.")
        
        if role not in ['proprietaire', 'client', 'locataire']:
            errors.append("Rôle invalide.")
        
        if not password or len(password) < 8:
            errors.append("Le mot de passe doit contenir au moins 8 caractères.")
        else:
            if not re.search(r'[A-Z]', password):
                errors.append("Le mot de passe doit contenir au moins une majuscule.")
            if not re.search(r'[a-z]', password):
                errors.append("Le mot de passe doit contenir au moins une minuscule.")
            if not re.search(r'\d', password):
                errors.append("Le mot de passe doit contenir au moins un chiffre.")
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                errors.append("Le mot de passe doit contenir au moins un caractère spécial.")
        
        if password != confirmation:
            errors.append("Les mots de passe ne correspondent pas.")
        
        if not conditions:
            errors.append("Vous devez accepter les conditions d'utilisation.")
        
        if errors:
            context = {
                'errors': errors,
                'nom': nom,
                'prenom': prenom,
                'email': email,
                'telephone': telephone,
                'role': role,
            }
            return render(request, 'accounts/register.html', context)
        
        try:
            base_username = f"{prenom.lower()}.{nom.lower()}"
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=prenom,
                last_name=nom
            )
            
            login(request, user)
            messages.success(request, f"Bienvenue {prenom} ! Votre compte a été créé avec succès.")
            
            if role in ['proprietaire']:
                return redirect('accounts:verify_owner')
            else:
                return redirect('home')
                
        except IntegrityError as e:
            messages.error(request, "Une erreur est survenue lors de la création du compte.")
            return redirect('accounts:register')
    
    return render(request, 'accounts/register.html')


def logout_view(request):
    """Déconnexion"""
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect('home')


@login_required
def profile(request):
    """Page de profil"""
    return render(request, 'accounts/profile.html', {'user': request.user})


@login_required
def edit_profile(request):
    """Modification du profil"""
    return render(request, 'accounts/edit_profile.html', {'user': request.user})


def password_reset(request):
    """Réinitialisation du mot de passe"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'

        if not email or not re.match(email_pattern, email):
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Veuillez entrer une adresse email valide.'})
            messages.error(request, 'Veuillez entrer une adresse email valide.')
            return render(request, 'accounts/password_reset.html')

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Si cet email est associé à un compte, un lien de réinitialisation a été envoyé.'
            })

        messages.success(request, 'Si cet email est associé à un compte, un lien de réinitialisation a été envoyé.')
        return render(request, 'accounts/password_reset.html')

    return render(request, 'accounts/password_reset.html')

@login_required
def verify_owner(request):
    """
    Formulaire de vérification pour les propriétaires
    URL: /accounts/verify-owner/
    Template: accounts/verify_owner.html
    """
    user = request.user
    
    try:
        verification = OwnerVerification.objects.get(user=user)
        if verification.is_approved():
            messages.info(request, "Vous êtes déjà vérifié.")
            return redirect('accounts:profile')
        
        if verification.is_pending():
            messages.info(request, "Votre demande de vérification est déjà en cours de traitement.")
            return redirect('accounts:verification_status')
    except OwnerVerification.DoesNotExist:
        verification = None
    
    if request.method == 'POST':
        identity_document = request.FILES.get('identity_document')
        proof_of_ownership = request.FILES.get('proof_of_ownership')
        tax_identification = request.FILES.get('tax_identification')
        
        errors = []
        
        if not identity_document:
            errors.append("La pièce d'identité est obligatoire.")
        
        if not proof_of_ownership:
            errors.append("Le justificatif de propriété est obligatoire.")
        
        if identity_document:
            if not identity_document.name.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                errors.append("La pièce d'identité doit être au format PDF, JPG, JPEG ou PNG.")
        
        if proof_of_ownership:
            if not proof_of_ownership.name.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                errors.append("Le justificatif de propriété doit être au format PDF, JPG, JPEG ou PNG.")
        
        if errors:
            context = {
                'errors': errors,
                'verification': verification,
            }
            return render(request, 'accounts/verify_owner.html', context)
        
        if verification:
            verification.identity_document = identity_document
            verification.proof_of_ownership = proof_of_ownership
            if tax_identification:
                verification.tax_identification = tax_identification
            verification.status = 'pending'
            verification.admin_notes = ''
            verification.submitted_at = timezone.now()
            verification.save()
        else:
            verification = OwnerVerification.objects.create(
                user=user,
                identity_document=identity_document,
                proof_of_ownership=proof_of_ownership,
                tax_identification=tax_identification,
                status='pending'
            )
        
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            Notification.objects.create(
                user=admin,
                type='owner_verification',
                title='Nouvelle demande de vérification',
                message=f"Le propriétaire {user.username} a soumis une demande de vérification.",
                link='/dashboard/verifications/'
            )
        
        messages.success(request, "Vos documents ont été soumis avec succès. Vous serez notifié du résultat dans les 24-48h.")
        return redirect('accounts:verification_status')
    
    context = {
        'verification': verification,
    }
    return render(request, 'accounts/verify_owner.html', context)


@login_required
def verification_status(request):
    """
    Afficher le statut de la vérification
    URL: /accounts/verification-status/
    Template: accounts/verification_status.html
    """
    user = request.user
    
    try:
        verification = OwnerVerification.objects.get(user=user)
    except OwnerVerification.DoesNotExist:
        verification = None
    
    context = {
        'verification': verification,
    }
    return render(request, 'accounts/verification_status.html', context)


@login_required
def verifications_list(request):
    """
    Liste des demandes de vérification (Admin)
    URL: /dashboard/verifications/
    Template: dashboard/verifications_list.html
    """
    if not request.user.is_superuser:
        messages.error(request, "Vous n'avez pas les droits d'administrateur.")
        return redirect('home')
    
    verifications = OwnerVerification.objects.all().order_by('-submitted_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        verifications = verifications.filter(status=status_filter)
    
    context = {
        'verifications': verifications,
        'status_filter': status_filter,
    }
    return render(request, 'dashboard/verifications_list.html', context)


@login_required
def verification_process(request, verification_id):
    """
    Traiter une demande de vérification (Admin)
    URL: /dashboard/verification/<int:verification_id>/traiter/
    Template: dashboard/verification_process.html
    """
    if not request.user.is_superuser:
        messages.error(request, "Vous n'avez pas les droits d'administrateur.")
        return redirect('home')
    
    verification = get_object_or_404(OwnerVerification, id=verification_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            verification.approve(notes)
            
            Notification.objects.create(
                user=verification.user,
                type='owner_verification',
                title='✅ Vérification approuvée',
                message=f"Félicitations ! Votre compte propriétaire a été vérifié avec succès. Vous pouvez maintenant publier des annonces.",
                link='/properties/create/'
            )
            
            messages.success(request, f"Le propriétaire {verification.user.username} a été vérifié.")
            
        elif action == 'reject':
            verification.reject(notes)
            
            Notification.objects.create(
                user=verification.user,
                type='owner_verification',
                title='❌ Vérification rejetée',
                message=f"Votre demande de vérification a été rejetée. Raison : {notes if notes else 'Documents non conformes'}",
                link='/accounts/verify-owner/'
            )
            
            messages.info(request, f"La vérification de {verification.user.username} a été rejetée.")
        
        return redirect('dashboard:verifications_list')
    
    context = {
        'verification': verification,
    }
    return render(request, 'dashboard/verification_process.html', context)
    # accounts/views.py
