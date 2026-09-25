from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import OwnerRequest, OwnerVerification, UserProfile
from notifications.models import Notification
import re 
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordChangeView,
    PasswordResetView, PasswordResetConfirmView, PasswordResetDoneView,
    PasswordResetCompleteView,
)
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_http_methods

from .forms import (
    RegisterForm, LoginForm, ProfileForm, OwnerProfileForm,
    CustomPasswordChangeForm, EmailChangeForm, PreferencesForm,
    DeleteAccountForm,
)
from .services import EmailService, EmailChangeService, SessionService, AccountService

from django.contrib.admin.views.decorators import staff_member_required
from .models import OwnerRequest

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
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'phone_number': telephone,
                    'role': 'proprietaire' if role == 'proprietaire' else 'client',
                },
            )
            
            login(request, user)
            messages.success(request, f"Bienvenue {prenom} ! Votre compte a été créé avec succès.")
            
            if role == 'proprietaire':
                return redirect('accounts:redirect_after_login')
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
    return redirect('accounts:profile_edit')


@login_required
def change_password(request):
    """Change le mot de passe de l'utilisateur connecté."""
    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirmation = request.POST.get('confirmation', '')

        errors = []
        if not request.user.check_password(current_password):
            errors.append('Mot de passe actuel incorrect.')
        if new_password != confirmation:
            errors.append('Les mots de passe ne correspondent pas.')
        if not errors:
            try:
                validate_password(new_password, request.user)
            except ValidationError as exc:
                errors.extend(exc.messages)

        if errors:
            return render(request, 'accounts/change_password.html', {'errors': errors})

        request.user.set_password(new_password)
        request.user.save(update_fields=['password'])
        update_session_auth_hash(request, request.user)
        messages.success(request, 'Votre mot de passe a été modifié avec succès.')
        return redirect('accounts:profile')

    return render(request, 'accounts/change_password.html')


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
    Template: accounts/verification_statut.html
    """
    user = request.user
    
    try:
        verification = OwnerVerification.objects.get(user=user)
    except OwnerVerification.DoesNotExist:
        verification = None
    
    context = {
        'verification': verification,
    }
    return render(request, 'accounts/verification_statut.html', context)


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


@login_required
def delete_account(request):
    """
    Page de suppression de compte
    URL: /accounts/delete/
    Template: accounts/delete_account.html
    """
    user = request.user
    
    if request.method == 'POST':
        # ===== RÉCUPÉRATION DES DONNÉES =====
        password = request.POST.get('password')
        confirmation = request.POST.get('confirmation')  # Doit être "SUPPRIMER"
        reason = request.POST.get('reason', '')
        delete_type = request.POST.get('delete_type', 'deactivate')  # 'deactivate' ou 'delete'
        
        # ===== VALIDATION =====
        errors = []
        
        # Vérifier le mot de passe
        if not password:
            errors.append("Le mot de passe est obligatoire.")
        elif not user.check_password(password):
            errors.append("Mot de passe incorrect.")
        
        # Vérifier la confirmation
        if confirmation != 'SUPPRIMER':
            errors.append("Veuillez taper 'SUPPRIMER' pour confirmer.")
        
        if errors:
            context = {
                'errors': errors,
                'reason': reason,
                'delete_type': delete_type,
            }
            return render(request, 'accounts/delete_account.html', context)
        
        # ===== TRAITEMENT =====
        
        # Sauvegarder les informations pour la notification
        username = user.username
        email = user.email
        user_id = user.id
        
        # Notification à l'administrateur (avant suppression)
        try:
            admins = User.objects.filter(is_superuser=True)
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    type='system',
                    title='🗑️ Suppression de compte',
                    message=f"L'utilisateur {username} ({email}) a {'désactivé' if delete_type == 'deactivate' else 'supprimé'} son compte. Raison : {reason if reason else 'Non spécifiée'}",
                    link='/dashboard/admin/utilisateurs/'
                )
        except:
            pass
        
        # ===== TYPE DE SUPPRESSION =====
        if delete_type == 'deactivate':
            # Désactivation (conserve les données)
            user.is_active = False
            user.save()
            
            # Déconnexion
            logout(request)
            
            messages.success(
                request, 
                "Votre compte a été désactivé avec succès. Vous pouvez le réactiver en contactant l'administrateur."
            )
            return redirect('home')
            
        else:  # delete_type == 'delete'
            # Suppression définitive
            # Déconnexion d'abord
            logout(request)
            
            # Suppression de l'utilisateur
            # (Les relations CASCADE supprimeront automatiquement les données associées)
            user.delete()
            
            messages.success(
                request, 
                "Votre compte a été supprimé définitivement. Toutes vos données ont été effacées."
            )
            return redirect('home')
    
    # ===== AFFICHAGE DU FORMULAIRE =====
    # Statistiques pour avertir l'utilisateur
    properties_count = user.properties.count() if hasattr(user, 'properties') else 0
    bookings_count = user.client_bookings.count() if hasattr(user, 'client_bookings') else 0
    reviews_count = user.review_set.count() if hasattr(user, 'review_set') else 0
    messages_count = user.sent_messages.count() if hasattr(user, 'sent_messages') else 0
    
    context = {
        'properties_count': properties_count,
        'bookings_count': bookings_count,
        'reviews_count': reviews_count,
        'messages_count': messages_count,
        'has_properties': properties_count > 0,
        'has_bookings': bookings_count > 0,
        'has_reviews': reviews_count > 0,
        'has_messages': messages_count > 0,
    }
    
    return render(request, 'accounts/delete_account.html', context)


@login_required
def deactivate_account(request):
    """
    Désactivation rapide du compte (sans suppression)
    URL: /accounts/deactivate/
    """
    if request.method == 'POST':
        password = request.POST.get('password')
        
        if not request.user.check_password(password):
            messages.error(request, "Mot de passe incorrect.")
            return redirect('accounts:profile')
        
        user = request.user
        user.is_active = False
        user.save()
        
        logout(request)
        messages.info(request, "Votre compte a été désactivé. Contactez l'administrateur pour le réactiver.")
        return redirect('home')
    
    return redirect('accounts:delete_account')


@login_required
def delete_account_confirm(request):
    """
    Confirmation AJAX de suppression (optionnel)
    URL: /accounts/delete/confirm/
    """
    if request.method == 'POST':
        password = request.POST.get('password')
        
        if not request.user.check_password(password):
            return JsonResponse({
                'success': False,
                'error': 'Mot de passe incorrect'
            })
        
        return JsonResponse({
            'success': True,
            'message': 'Mot de passe vérifié'
        })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'}, status=405)


@login_required
def export_data(request):
    """
    Exporter les données de l'utilisateur avant suppression
    URL: /accounts/export-data/
    """
    import json
    from django.http import HttpResponse
    
    user = request.user
    
    # Collecter les données
    data = {
        'user': {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
        },
        'profile': {},
        'properties': [],
        'bookings': [],
        'reviews': [],
        'messages': [],
    }
    
    # Profil
    if hasattr(user, 'profile'):
        profile = user.profile
        data['profile'] = {
            'role': profile.role,
            'phone_number': profile.phone_number,
            'bio': profile.bio,
            'address': profile.address,
            'city': profile.city,
        }
    
    # Propriétés
    if hasattr(user, 'properties'):
        for prop in user.properties.all():
            data['properties'].append({
                'title': prop.title,
                'description': prop.description,
                'type': prop.property_type,
                'price': float(prop.price),
                'quartier': prop.quartier,
                'address': prop.address,
                'surface': prop.surface_area,
                'rooms': prop.number_rooms,
                'created_at': prop.created_at.strftime('%Y-%m-%d'),
            })
    
    # Réservations
    if hasattr(user, 'client_bookings'):
        for booking in user.client_bookings.all():
            data['bookings'].append({
                'property': booking.property.title,
                'start_date': booking.start_date.strftime('%Y-%m-%d'),
                'end_date': booking.end_date.strftime('%Y-%m-%d'),
                'total_price': float(booking.total_price),
                'status': booking.status,
                'created_at': booking.created_at.strftime('%Y-%m-%d'),
            })
    
    # Avis
    if hasattr(user, 'review_set'):
        for review in user.review_set.all():
            data['reviews'].append({
                'property': review.property.title,
                'rating': review.rating,
                'comment': review.comment,
                'created_at': review.created_at.strftime('%Y-%m-%d'),
            })
    
    # Créer la réponse JSON
    response = HttpResponse(
        json.dumps(data, indent=2, ensure_ascii=False),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="habiora_data_{user.username}.json"'



@login_required
def delete_account_confirm_final(request):
    """
    Confirmation finale de la suppression du compte
    URL: /accounts/delete/confirm-final/
    Template: accounts/delete_confirm_final.html
    """
    user = request.user
    
    if request.method == 'POST':
        # ===== RÉCUPÉRATION DES DONNÉES =====
        password = request.POST.get('password')
        confirmation_text = request.POST.get('confirmation_text')
        acknowledge = request.POST.get('acknowledge')
        
        # ===== VALIDATION =====
        errors = []
        
        # Vérifier le mot de passe
        if not password:
            errors.append("Le mot de passe est obligatoire.")
        elif not user.check_password(password):
            errors.append("Mot de passe incorrect.")
        
        # Vérifier la confirmation texte
        if confirmation_text != 'SUPPRIMER DÉFINITIVEMENT':
            errors.append("Veuillez taper exactement 'SUPPRIMER DÉFINITIVEMENT'.")
        
        # Vérifier la case à cocher
        if not acknowledge:
            errors.append("Vous devez cocher la case pour confirmer que vous comprenez les conséquences.")
        
        if errors:
            context = {
                'errors': errors,
                'user': user,
            }
            return render(request, 'accounts/delete_confirm_final.html', context)
        
        # ===== SAUVEGARDER LES INFOS POUR LA NOTIFICATION =====
        username = user.username
        email = user.email
        
        # ===== NOTIFIER L'ADMIN =====
        try:
            admins = User.objects.filter(is_superuser=True)
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    type='system',
                    title='🗑️ Compte supprimé définitivement',
                    message=f"L'utilisateur {username} ({email}) a supprimé définitivement son compte.",
                    link='/dashboard/admin/utilisateurs/'
                )
        except:
            pass
        
        # ===== SUPPRESSION DÉFINITIVE =====
        # Déconnexion d'abord
        logout(request)
        
        # Supprimer l'utilisateur (les CASCADE supprimeront les données liées)
        try:
            user_obj = User.objects.get(username=username)
            user_obj.delete()
        except User.DoesNotExist:
            pass
        
        # Message de confirmation
        messages.success(
            request,
            f"Votre compte a été supprimé définitivement. Nous sommes désolés de vous voir partir."
        )
        
        return redirect('home')
    
    # ===== AFFICHAGE DE LA PAGE =====
    # Récapitulatif des données
    properties_count = user.properties.count() if hasattr(user, 'properties') else 0
    bookings_count = user.client_bookings.count() if hasattr(user, 'client_bookings') else 0
    owner_bookings_count = user.owner_bookings.count() if hasattr(user, 'owner_bookings') else 0
    reviews_count = user.review_set.count() if hasattr(user, 'review_set') else 0
    messages_count = user.sent_messages.count() if hasattr(user, 'sent_messages') else 0
    notifications_count = user.notifications.count() if hasattr(user, 'notifications') else 0
    
    # Calculer le total des données
    total_data = (
        properties_count + 
        bookings_count + 
        owner_bookings_count + 
        reviews_count + 
        messages_count + 
        notifications_count
    )
    
    context = {
        'user': user,
        'properties_count': properties_count,
        'bookings_count': bookings_count,
        'owner_bookings_count': owner_bookings_count,
        'reviews_count': reviews_count,
        'messages_count': messages_count,
        'notifications_count': notifications_count,
        'total_data': total_data,
        'has_data': total_data > 0,
    }
    
    return render(request, 'accounts/delete_confirm_final.html', context)


@login_required
def verify_delete_password(request):
    """
    Vérification AJAX du mot de passe avant suppression
    URL: /accounts/delete/verify-password/
    """
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        password = data.get('password', '')
        
        if not password:
            return JsonResponse({
                'success': False,
                'error': 'Mot de passe requis'
            })
        
        if request.user.check_password(password):
            return JsonResponse({
                'success': True,
                'message': 'Mot de passe vérifié'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Mot de passe incorrect'
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'}, status=405)


@login_required
def cancel_deletion(request):
    """
    Annuler la demande de suppression
    URL: /accounts/delete/cancel/
    """
    messages.info(request, "Suppression annulée. Votre compte est conservé.")
    return redirect('accounts:profile')


@login_required
def export_data_before_delete(request):
    """
    Exporter les données avant suppression définitive
    URL: /accounts/delete/export/
    """
    import json
    from django.http import HttpResponse
    
    user = request.user
    
    # Collecter toutes les données
    data = {
        'export_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        'user': {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
        },
        'profile': {},
        'properties': [],
        'bookings': [],
        'owner_bookings': [],
        'reviews': [],
        'notifications': [],
    }
    
    # Profil
    if hasattr(user, 'profile'):
        profile = user.profile
        data['profile'] = {
            'role': profile.role,
            'phone_number': profile.phone_number,
            'bio': profile.bio,
            'address': profile.address,
            'city': profile.city,
            'is_verified': profile.is_verified,
            'created_at': profile.created_at.strftime('%Y-%m-%d'),
        }
    
    # Propriétés
    if hasattr(user, 'properties'):
        for prop in user.properties.all():
            data['properties'].append({
                'id': prop.id,
                'title': prop.title,
                'description': prop.description,
                'type': prop.property_type,
                'price': float(prop.price),
                'quartier': prop.quartier,
                'address': prop.address,
                'surface': prop.surface_area,
                'rooms': prop.number_rooms,
                'bathrooms': prop.number_bathrooms,
                'is_approved': prop.is_approved,
                'is_active': prop.is_active,
                'views': prop.views_count,
                'created_at': prop.created_at.strftime('%Y-%m-%d'),
            })
    
    # Réservations (client)
    if hasattr(user, 'client_bookings'):
        for booking in user.client_bookings.all():
            data['bookings'].append({
                'id': booking.id,
                'property': booking.property.title,
                'start_date': booking.start_date.strftime('%Y-%m-%d'),
                'end_date': booking.end_date.strftime('%Y-%m-%d'),
                'total_price': float(booking.total_price),
                'status': booking.status,
                'created_at': booking.created_at.strftime('%Y-%m-%d'),
            })
    
    # Réservations (propriétaire)
    if hasattr(user, 'owner_bookings'):
        for booking in user.owner_bookings.all():
            data['owner_bookings'].append({
                'id': booking.id,
                'property': booking.property.title,
                'client': booking.client.username,
                'start_date': booking.start_date.strftime('%Y-%m-%d'),
                'end_date': booking.end_date.strftime('%Y-%m-%d'),
                'total_price': float(booking.total_price),
                'status': booking.status,
                'created_at': booking.created_at.strftime('%Y-%m-%d'),
            })
    
    # Avis
    if hasattr(user, 'review_set'):
        for review in user.review_set.all():
            data['reviews'].append({
                'id': review.id,
                'property': review.property.title,
                'rating': review.rating,
                'comment': review.comment,
                'created_at': review.created_at.strftime('%Y-%m-%d'),
            })
    
    # Notifications
    if hasattr(user, 'notifications'):
        for notif in user.notifications.all()[:100]:  # Limiter à 100
            data['notifications'].append({
                'type': notif.type,
                'title': notif.title,
                'message': notif.message,
                'is_read': notif.is_read,
                'created_at': notif.created_at.strftime('%Y-%m-%d %H:%M'),
            })
    
    # Créer la réponse
    response = HttpResponse(
        json.dumps(data, indent=2, ensure_ascii=False),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="habiora_data_{user.username}_{timezone.now().strftime("%Y%m%d")}.json"'
    
   

# ---------- AUTH ----------

def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:redirect_after_login')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            EmailService.send_welcome(user)
            messages.success(request, "Bienvenue !")
            return redirect('accounts:redirect_after_login')
    else:
        form = RegisterForm()
    return render(request, 'accounts/auth/register.html', {'form': form})


class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = 'accounts/auth/login.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        from .services import LoginHistoryService
        LoginHistoryService.log(self.request, user=self.request.user, success=True)
        return response

    def form_invalid(self, form):
        from .services import LoginHistoryService
        LoginHistoryService.log(
            self.request, success=False,
            reason='invalid_credentials',
            email=form.data.get('username', '')
        )
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('accounts:redirect_after_login')


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')


def redirect_after_login(request):
    user = request.user
    if user.role == 'admin':
        return redirect('/admin/')
    if user.is_owner:
        return redirect('owner:dashboard')
    return redirect('dashboard:home')


# ---------- PROFIL ----------

@login_required
def profile_view(request):
    return render(request, 'accounts/profile/view.html', {
        'profile': request.user.profile,
        'sessions': SessionService.list_for_user(request.user)[:3],
    })


@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour.")
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user.profile)
    return render(request, 'accounts/profile/edit.html', {'form': form})


@login_required
def owner_profile_edit(request):
    if not request.user.is_owner:
        messages.error(request, "Vous n'êtes pas propriétaire.")
        return redirect('accounts:profile')
    if request.method == 'POST':
        form = OwnerProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Informations professionnelles mises à jour.")
            return redirect('accounts:profile')
    else:
        form = OwnerProfileForm(instance=request.user.profile)
    return render(request, 'accounts/profile/owner_edit.html', {'form': form})


class CustomPasswordChangeView(PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'accounts/profile/password.html'
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        update_session_auth_hash(self.request, form.user)
        SessionService.revoke_all(
            self.request.user,
            except_session_key=self.request.session.session_key
        )
        EmailService.send_password_changed(self.request.user)
        messages.success(self.request, "Mot de passe modifié. Autres sessions déconnectées.")
        return response


@login_required
def email_change_request(request):
    if request.method == 'POST':
        form = EmailChangeForm(request.user, request.POST)
        if form.is_valid():
            req = EmailChangeService.create_request(
                request.user, form.cleaned_data['new_email']
            )
            EmailService.send_email_change_confirmation(req, request)
            messages.info(request, f"Un email de confirmation a été envoyé à {req.new_email}.")
            return redirect('accounts:profile')
    else:
        form = EmailChangeForm(request.user)
    return render(request, 'accounts/profile/email.html', {'form': form})


@require_http_methods(["GET"])
def confirm_email_change(request, token):
    try:
        user = EmailChangeService.confirm(token)
        messages.success(request, f"Votre email a été changé en {user.email}.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('accounts:login')


@login_required
def preferences_view(request):
    if request.method == 'POST':
        form = PreferencesForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Préférences enregistrées.")
            return redirect('accounts:preferences')
    else:
        form = PreferencesForm(instance=request.user.profile)
    return render(request, 'accounts/profile/preferences.html', {'form': form})


@login_required
def sessions_view(request):
    return render(request, 'accounts/profile/sessions.html', {
        'sessions': SessionService.list_for_user(request.user),
        'current_session_key': request.session.session_key,
    })


@login_required
@require_http_methods(["POST"])
def revoke_session(request, session_id):
    try:
        SessionService.revoke(request.user, session_id)
        messages.success(request, "Session déconnectée.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('accounts:sessions')


@login_required
@require_http_methods(["POST"])
def revoke_all_sessions(request):
    SessionService.revoke_all(request.user, except_session_key=request.session.session_key)
    messages.success(request, "Toutes les autres sessions ont été déconnectées.")
    return redirect('accounts:sessions')


@login_required
def delete_account(request):
    if request.method == 'POST':
        form = DeleteAccountForm(request.user, request.POST)
        if form.is_valid():
            AccountService.anonymize(request.user)
            logout(request)
            messages.success(request, "Votre compte a été supprimé.")
            return redirect('accounts:login')
    else:
        form = DeleteAccountForm(request.user)
    return render(request, 'accounts/profile/delete.html', {'form': form})


# ---------- DEVENIR PROPRIÉTAIRE ----------

@login_required
def become_owner(request):
    if request.user.is_owner:
        return redirect('owner:dashboard')
    if request.method == 'POST':
        request.user.promote_to_owner()
        messages.success(request, "Vous êtes maintenant propriétaire !")
        return redirect('owner:dashboard')
    return render(request, 'accounts/become_owner.html')

    # accounts/views.py — MODIFIER register_view

def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:redirect_after_login')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # ⚠️ NE PAS donner is_owner tout de suite
            role = form.cleaned_data['role']
            if role == 'owner':
                user.role = 'client'      # reste client tant que pas validé
                user.is_owner = False
            else:
                user.role = 'client'
                user.is_owner = False
            user.save()

            # Si propriétaire → créer la demande
            if role == 'owner':
                OwnerRequest.objects.create(user=user, status='pending')

            login(request, user)
            EmailService.send_welcome(user)

            if role == 'owner':
                messages.info(request, "Complétez votre dossier propriétaire.")
                return redirect('accounts:owner_request_form')

            return redirect('accounts:redirect_after_login')
    else:
        form = RegisterForm()

    return render(request, 'accounts/auth/register.html', {'form': form})

    # accounts/views.py — AJOUTER

@login_required
def owner_request_form(request):
    """Formulaire de dossier propriétaire"""
    if request.user.is_owner:
        return redirect('owner:dashboard')

    req = getattr(request.user, 'owner_request', None)

    if request.method == 'POST':
        form = OwnerRequestForm(request.POST, instance=req)
        if form.is_valid():
            OwnerRequestService.create_or_update(request.user, form.cleaned_data)
            messages.success(request, "Dossier envoyé. Un administrateur va l'examiner.")
            return redirect('accounts:owner_request_status')
    else:
        form = OwnerRequestForm(instance=req)

    return render(request, 'accounts/owner/request_form.html', {'form': form})


@login_required
def owner_request_status(request):
    """Statut de la demande"""
    req = getattr(request.user, 'owner_request', None)
    if not req:
        return redirect('accounts:owner_request_form')

    return render(request, 'accounts/owner/request_status.html', {'req': req})

    # accounts/views.py — MODIFIER redirect_after_login

def redirect_after_login(request):
    user = request.user
    if user.is_superuser or user.is_staff:
        return redirect('dashboard:admin_dashboard')

    profile = UserProfile.objects.filter(user=user).first()
    if profile and profile.role == 'proprietaire':
        return redirect('dashboard:owner_dashboard')

    if OwnerVerification.objects.filter(user=user).exists():
        return redirect('dashboard:owner_dashboard')

    if OwnerRequest.objects.filter(user=user).exists():
        return redirect('dashboard:owner_dashboard')

    return redirect('dashboard:client_dashboard')

    # accounts/views.py — AJOUTER

@staff_member_required
def admin_owner_requests(request):
    """Liste des demandes en attente"""
    status = request.GET.get('status', 'pending')
    qs = OwnerRequest.objects.select_related('user').filter(status=status)
    return render(request, 'accounts/admin/owner_requests.html', {
        'requests': qs,
        'current_status': status,
    })


@staff_member_required
def admin_owner_request_detail(request, pk):
    """Détail d'une demande"""
    req = get_object_or_404(OwnerRequest.objects.select_related('user'), pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'approve':
                OwnerRequestService.approve(req, request.user)
                messages.success(request, f"{req.user.email} est maintenant propriétaire.")
            elif action == 'reject':
                reason = request.POST.get('reason', '').strip()
                OwnerRequestService.reject(req, request.user, reason)
                messages.success(request, f"Demande de {req.user.email} rejetée.")
            return redirect('accounts:admin_owner_requests')
        except ValueError as e:
            messages.error(request, str(e))

    return render(request, 'accounts/admin/owner_request_detail.html', {'req': req})
    # accounts/views.py
