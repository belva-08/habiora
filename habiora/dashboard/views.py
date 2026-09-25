from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from django.contrib.auth.models import User
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import timedelta
from chat.models import Conversation, Message
from properties.models import Property, PropertyImage
from bookings.models import Booking
from reviews.models import Review, IncidentReport
from accounts.models import UserProfile, OwnerVerification
from notifications.models import Notification
from .models import AdminActionLog

from favorites.models import Favorite  
from search.models import SearchHistory  
from django.http import JsonResponse
from properties.models import Property, PropertyImage
from chat.models import Conversation, Message
from calendar import monthrange
import json
from django.core.paginator import Paginator
from .models import AdminActionLog
from django.contrib.admin.views.decorators import staff_member_required
from .models import VerificationRequest, VerificationLog
from .forms import ApproveForm, RejectForm
from .services import VerificationService

def admin_required(view_func):
    """Décorateur pour restreindre aux administrateurs"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Veuillez vous connecter.")
            return redirect('accounts:login')
        
        if not request.user.is_superuser and not request.user.is_staff:
            messages.error(request, "Vous n'avez pas les droits d'administrateur.")
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
@admin_required
def admin_dashboard(request):
    """Tableau de bord administrateur"""
    
    total_users = User.objects.count()
    total_properties = Property.objects.count()
    total_bookings = Booking.objects.count()
    total_reviews = Review.objects.count()
    
    users_by_role = {
        'clients': User.objects.filter(is_superuser=False, is_staff=False).count(),
        'proprietaires': User.objects.filter(is_superuser=False, is_staff=False).count(),  # À adapter si vous avez un champ role
        'admins': User.objects.filter(Q(is_superuser=True) | Q(is_staff=True)).count(),
    }
    
    week_ago = timezone.now() - timedelta(days=7)
    active_users = User.objects.filter(last_login__gte=week_ago).count()
    
    properties_by_status = {
        'en_attente': Property.objects.filter(is_approved=False).count(),
        'approuvees': Property.objects.filter(is_approved=True).count(),
        'actives': Property.objects.filter(is_approved=True, is_active=True).count(),
        'desactivees': Property.objects.filter(is_approved=True, is_active=False).count(),
    }
    
    bookings_by_status = {
        'en_attente': Booking.objects.filter(status='pending').count(),
        'confirmees': Booking.objects.filter(status='confirmed').count(),
        'terminees': Booking.objects.filter(status='completed').count(),
        'annulees': Booking.objects.filter(status='cancelled').count(),
    }
    
    pending_properties = Property.objects.filter(is_approved=False).order_by('-created_at')[:10]
    pending_properties_count = pending_properties.count()
    
    pending_verifications = OwnerVerification.objects.filter(status='pending').order_by('-submitted_at')[:10]
    pending_verifications_count = pending_verifications.count()
    
    pending_incidents = IncidentReport.objects.filter(status='pending').order_by('-created_at')[:10]
    pending_incidents_count = pending_incidents.count()
    
    recent_activities = AdminActionLog.objects.select_related('admin').order_by('-created_at')[:20]
    
    notifications = Notification.objects.filter(user=request.user, is_read=False)[:10]
    
    context = {
        'total_users': total_users,
        'total_properties': total_properties,
        'total_bookings': total_bookings,
        'total_reviews': total_reviews,
        'active_users': active_users,
        'users_by_role': users_by_role,
        'properties_by_status': properties_by_status,
        'bookings_by_status': bookings_by_status,
        
        'pending_properties': pending_properties,
        'pending_properties_count': pending_properties_count,
        'pending_verifications': pending_verifications,
        'pending_verifications_count': pending_verifications_count,
        'pending_incidents': pending_incidents,
        'pending_incidents_count': pending_incidents_count,
        
        'recent_activities': recent_activities,
        'notifications': notifications,
    }
    
    return render(request, 'dashboard/admin.html', context)


@login_required
@admin_required
def users_list(request):
    """Liste des utilisateurs"""
    users = User.objects.all().order_by('-date_joined')

    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    role_filter = request.GET.get('role')
    if role_filter:
        if role_filter == 'admin':
            users = users.filter(Q(is_superuser=True) | Q(is_staff=True))
        elif role_filter == 'client':
            users = users.filter(is_superuser=False, is_staff=False)
    
    context = {
        'users': users,
        'search': search,
        'role_filter': role_filter,
    }
    return render(request, 'dashboard/users_list.html', context)


@login_required
@admin_required
def user_detail(request, user_id):
    user_obj = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    user_type = 'admin' if user_obj.is_superuser or user_obj.is_staff else (
        'proprietaire' if user_obj.properties.exists() else 'client'
    )
    verification = getattr(user_obj, 'owner_verification', None)

    context = {
        'user_obj': user_obj,
        'user_type': user_type,
        'verification': verification,
        'total_properties': user_obj.properties.count(),
    }
    return render(request, 'dashboard/user_detail.html', context)


@login_required
@admin_required
def users_export(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="utilisateurs.csv"'
    writer = csv.writer(response)
    writer.writerow(['Nom utilisateur', 'Email', 'Actif', 'Date inscription'])
    for user in User.objects.all().order_by('username'):
        writer.writerow([
            user.username,
            user.email,
            'Oui' if user.is_active else 'Non',
            user.date_joined.strftime('%d/%m/%Y'),
        ])
    return response


@login_required
@admin_required
def users_bulk_action(request):
    if request.method == 'POST':
        user_ids = request.POST.getlist('user_ids')
        action = request.POST.get('action')
        users = User.objects.filter(id__in=user_ids, is_superuser=False)

        if action == 'activate':
            users.update(is_active=True)
            messages.success(request, 'Les utilisateurs sélectionnés ont été activés.')
        elif action == 'deactivate':
            users.update(is_active=False)
            messages.success(request, 'Les utilisateurs sélectionnés ont été désactivés.')
        elif action == 'delete':
            users.delete()
            messages.success(request, 'Les utilisateurs sélectionnés ont été supprimés.')

    return redirect('dashboard:users_list')


@login_required
@admin_required
def user_toggle_active(request, user_id):
    """Activer/Désactiver un utilisateur"""
    user = get_object_or_404(User, id=user_id)
    
    if user.is_superuser:
        messages.error(request, "Vous ne pouvez pas désactiver un superutilisateur.")
        return redirect('dashboard:users_list')
    
    user.is_active = not user.is_active
    user.save()
    
    status = "activé" if user.is_active else "désactivé"
    messages.success(request, f"L'utilisateur {user.username} a été {status}.")
    
    AdminActionLog.objects.create(
        admin=request.user,
        action_type='user_activate' if user.is_active else 'user_deactivate',
        description=f"Utilisateur {user.username} {status}",
        target_user=user
    )
    
    return redirect('dashboard:users_list')


@login_required
@admin_required
def user_delete(request, user_id):
    """Supprimer un utilisateur"""
    user = get_object_or_404(User, id=user_id)
    
    if user.is_superuser:
        messages.error(request, "Vous ne pouvez pas supprimer un superutilisateur.")
        return redirect('dashboard:users_list')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"L'utilisateur {username} a été supprimé.")
        return redirect('dashboard:users_list')
    
    return render(request, 'dashboard/user_delete.html', {'user': user})


@login_required
@admin_required
def properties_list(request):
    """Liste des annonces"""
    properties = Property.objects.all().order_by('-created_at')
    
    status = request.GET.get('status')
    if status == 'pending':
        properties = properties.filter(is_approved=False)
    elif status == 'approved':
        properties = properties.filter(is_approved=True)
    elif status == 'active':
        properties = properties.filter(is_approved=True, is_active=True)
    elif status == 'inactive':
        properties = properties.filter(is_approved=True, is_active=False)
    
    search = request.GET.get('search')
    if search:
        properties = properties.filter(
            Q(title__icontains=search) |
            Q(address__icontains=search) |
            Q(quartier__icontains=search)
        )
    
    context = {
        'properties': properties,
        'status': status,
        'search': search,
    }
    return render(request, 'dashboard/properties_list.html', context)


@login_required
@admin_required
def property_validate(request, property_id):
    """Valider ou rejeter une annonce"""
    property = get_object_or_404(Property, id=property_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('reason', '')
        
        if action == 'approve':
            property.is_approved = True
            property.is_active = True
            property.save()
            
            Notification.objects.create(
                user=property.owner,
                type='property_validation',
                title='Annonce approuvée',
                message=f"Votre annonce '{property.title}' a été approuvée et est maintenant en ligne.",
                link=f'/properties/{property.id}/'
            )
            
            AdminActionLog.objects.create(
                admin=request.user,
                action_type='property_approve',
                description=f"Annonce '{property.title}' approuvée",
                target_property=property
            )
            
            messages.success(request, f"L'annonce '{property.title}' a été approuvée.")
            
        elif action == 'reject':
            property.is_approved = False
            property.save()
            
            Notification.objects.create(
                user=property.owner,
                type='property_rejection',
                title='Annonce rejetée',
                message=f"Votre annonce '{property.title}' a été rejetée. Raison : {reason if reason else 'Non conforme aux critères'}",
                link=f'/properties/{property.id}/'
            )
            
            AdminActionLog.objects.create(
                admin=request.user,
                action_type='property_reject',
                description=f"Annonce '{property.title}' rejetée",
                target_property=property
            )
            
            messages.info(request, f"L'annonce '{property.title}' a été rejetée.")
        
        return redirect('dashboard:properties_list')
    
    return render(request, 'dashboard/property_validate.html', {'property': property})


@login_required
@admin_required
def property_delete(request, property_id):
    """Supprimer une annonce"""
    property = get_object_or_404(Property, id=property_id)
    
    if request.method == 'POST':
        title = property.title
        property.delete()
        
        AdminActionLog.objects.create(
            admin=request.user,
            action_type='property_delete',
            description=f"Annonce '{title}' supprimée"
        )
        
        messages.success(request, f"L'annonce '{title}' a été supprimée.")
        return redirect('dashboard:properties_list')
    
    return render(request, 'dashboard/property_delete.html', {'property': property})


@login_required
@admin_required
def verifications_list(request):
    """Liste des demandes de vérification"""
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
@admin_required
def verification_process(request, verification_id):
    """Traiter une demande de vérification"""
    verification = get_object_or_404(OwnerVerification, id=verification_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            verification.status = 'approved'
            verification.verified_at = timezone.now()
            verification.admin_notes = notes
            verification.save()
            
            user = verification.user
            user.save()
            
            Notification.objects.create(
                user=user,
                type='owner_verification',
                title='Vérification approuvée',
                message="Félicitations ! Votre compte propriétaire a été vérifié avec succès.",
            )
            
            AdminActionLog.objects.create(
                admin=request.user,
                action_type='owner_verify',
                description=f"Propriétaire {user.username} vérifié",
                target_user=user
            )
            
            messages.success(request, f"Le propriétaire {user.username} a été vérifié.")
            
        elif action == 'reject':
            verification.status = 'rejected'
            verification.admin_notes = notes
            verification.save()

            Notification.objects.create(
                user=verification.user,
                type='owner_verification',
                title='Vérification rejetée',
                message=f"Votre demande de vérification a été rejetée. Raison : {notes if notes else 'Documents non conformes'}",
            )
            
            messages.info(request, f"La vérification de {verification.user.username} a été rejetée.")
        
        return redirect('dashboard:verifications_list')
    
    return render(request, 'dashboard/verification_process.html', {'verification': verification})

@login_required
@admin_required
def incidents_list(request):
    """Liste des signalements"""
    incidents = IncidentReport.objects.all().order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        incidents = incidents.filter(status=status_filter)
    
    context = {
        'incidents': incidents,
        'status_filter': status_filter,
    }
    return render(request, 'dashboard/incidents_list.html', context)


@login_required
@admin_required
def incident_process(request, incident_id):
    """Traiter un signalement"""
    incident = get_object_or_404(IncidentReport, id=incident_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'resolve':
            incident.status = 'resolved'
            incident.admin_notes = notes
            incident.save()
        
            AdminActionLog.objects.create(
                admin=request.user,
                action_type='incident_resolve',
                description=f"Signalement #{incident.id} résolu"
            )
            
            messages.success(request, f"Le signalement #{incident.id} a été résolu.")
            
        elif action == 'reject':
            incident.status = 'rejected'
            incident.admin_notes = notes
            incident.save()
            
            messages.info(request, f"Le signalement #{incident.id} a été rejeté.")
        
        return redirect('dashboard:incidents_list')
    
    return render(request, 'dashboard/incident_process.html', {'incident': incident})

@login_required
@admin_required
def admin_statistics(request):
    """Statistiques détaillées"""
    
    current_month = timezone.now().month
    current_year = timezone.now().year
    
    users_by_month = []
    for i in range(5, -1, -1):
        month = timezone.now().month - i
        year = timezone.now().year
        if month <= 0:
            month += 12
            year -= 1
        
        start_date = timezone.datetime(year, month, 1)
        if month == 12:
            end_date = timezone.datetime(year + 1, 1, 1)
        else:
            end_date = timezone.datetime(year, month + 1, 1)
        
        count = User.objects.filter(date_joined__gte=start_date, date_joined__lt=end_date).count()
        users_by_month.append({
            'month': start_date.strftime('%b %Y'),
            'count': count
        })
    
    properties_by_month = []
    for i in range(5, -1, -1):
        month = timezone.now().month - i
        year = timezone.now().year
        if month <= 0:
            month += 12
            year -= 1
        
        start_date = timezone.datetime(year, month, 1)
        if month == 12:
            end_date = timezone.datetime(year + 1, 1, 1)
        else:
            end_date = timezone.datetime(year, month + 1, 1)
        
        count = Property.objects.filter(created_at__gte=start_date, created_at__lt=end_date).count()
        properties_by_month.append({
            'month': start_date.strftime('%b %Y'),
            'count': count
        })
    
    top_quartiers = Property.objects.values('quartier').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    top_owners = User.objects.annotate(
        property_count=Count('properties')
    ).order_by('-property_count')[:5]
    
    context = {
        'users_by_month': users_by_month,
        'properties_by_month': properties_by_month,
        'top_quartiers': top_quartiers,
        'top_owners': top_owners,
    }
    
    return render(request, 'dashboard/admin_statistics.html', context)

@login_required
@admin_required
def admin_notifications(request):
    """Notifications de l'admin"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    if request.method == 'POST':
        notification_id = request.POST.get('notification_id')
        if notification_id:
            notification = get_object_or_404(Notification, id=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            return redirect('dashboard:admin_notifications')
    
    return render(request, 'dashboard/admin_notifications.html', {'notifications': notifications})


@login_required
@admin_required
def mark_all_read(request):
    """Marquer toutes les notifications comme lues"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "Toutes les notifications ont été marquées comme lues.")
    return redirect('dashboard:admin_notifications')

@login_required
@admin_required
def check_notifications(request):
    """Vérifier les nouvelles notifications (AJAX)"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})

  

@login_required
def client_dashboard(request):
    """
    Tableau de bord du client
    URL: /dashboard/client/
    Template: dashboard/client.html
    """
    user = request.user
    
    total_bookings = Booking.objects.filter(tenant=user).count()
    pending_bookings = Booking.objects.filter(tenant=user, status='pending').count()
    confirmed_bookings = Booking.objects.filter(tenant=user, status='confirmed').count()
    completed_bookings = Booking.objects.filter(tenant=user, status='completed').count()
    cancelled_bookings = Booking.objects.filter(tenant=user, status='cancelled').count()
    
    upcoming_bookings = Booking.objects.filter(
        tenant=user,
        status='confirmed',
        start_date__gte=timezone.now().date()
    ).order_by('start_date')[:5]
    
    total_reviews = Review.objects.filter(author=user).count()
    
    try:
        favorites_count = Favorite.objects.filter(user=user).count()
    except:
        favorites_count = 0
    
    unread_messages = Message.objects.filter(
        conversation__participants=user,
        is_read=False
    ).exclude(sender=user).count()
    
    unread_notifications = Notification.objects.filter(
        user=user,
        is_read=False
    ).count()
    
    recent_bookings = Booking.objects.filter(
        tenant=user
    ).order_by('-created_at')[:5]
    
    recent_notifications = Notification.objects.filter(
        user=user
    ).order_by('-created_at')[:5]
    
    recent_conversations = Conversation.objects.filter(
        participants=user
    ).order_by('-updated_at')[:5]

    recommended_properties = Property.objects.filter(
        is_approved=True,
        is_active=True
    ).order_by('-created_at')[:6]
    
    context = {
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
        'confirmed_bookings': confirmed_bookings,
        'completed_bookings': completed_bookings,
        'cancelled_bookings': cancelled_bookings,
        'total_reviews': total_reviews,
        'favorites_count': favorites_count,
        'unread_messages': unread_messages,
        'unread_notifications': unread_notifications,
        
        'upcoming_bookings': upcoming_bookings,
        'recent_bookings': recent_bookings,
        'recent_notifications': recent_notifications,
        'recent_conversations': recent_conversations,
        'recommended_properties': recommended_properties,
    }
    
    return render(request, 'dashboard/client.html', context)

@login_required
def client_bookings(request):
    """
    Liste des réservations du client
    URL: /dashboard/client/bookings/
    Template: dashboard/client_bookings.html
    """
    user = request.user
    
    bookings = Booking.objects.filter(tenant=user).order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    context = {
        'bookings': bookings,
        'status_filter': status_filter,
    }
    return render(request, 'dashboard/client_bookings.html', context)


@login_required
def client_booking_detail(request, booking_id):
    """
    Détail d'une réservation
    URL: /dashboard/client/booking/<int:booking_id>/
    Template: dashboard/client_booking_detail.html
    """
    booking = get_object_or_404(Booking, id=booking_id, tenant=request.user)
    
    context = {
        'booking': booking,
    }
    return render(request, 'dashboard/client_booking_detail.html', context)


@login_required
def client_booking_cancel(request, booking_id):
    """
    Annuler une réservation
    URL: /dashboard/client/booking/<int:booking_id>/cancel/
    """
    booking = get_object_or_404(Booking, id=booking_id, tenant=request.user)
    
    if booking.status in ['cancelled', 'completed']:
        messages.warning(request, "Cette réservation ne peut pas être annulée.")
        return redirect('dashboard:client_booking_detail', booking_id=booking.id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        booking.status = 'cancelled'
        booking.save()
        
        Notification.objects.create(
                user=booking.property.owner,
            type='booking_cancelled',
            title='Réservation annulée',
            message=f"Le client {request.user.username} a annulé la réservation pour {booking.property.title}.",
            link=f'/bookings/{booking.id}/'
        )
        
        messages.success(request, "Votre réservation a été annulée avec succès.")
        return redirect('dashboard:client_bookings')
    
    return render(request, 'dashboard/client_booking_cancel.html', {'booking': booking})

@login_required
def client_favorites(request):
    """
    Liste des favoris du client
    URL: /dashboard/client/favorites/
    Template: dashboard/client_favorites.html
    """
    try:
        from favorites.models import Favorite
        favorites = Favorite.objects.filter(user=request.user).order_by('-created_at')
    except:
        favorites = []
    
    context = {
        'favorites': favorites,
    }
    return render(request, 'dashboard/client_favorites.html', context)

@login_required
def client_reviews(request):
    """
    Liste des avis du client
    URL: /dashboard/client/reviews/
    Template: dashboard/client_reviews.html
    """
    reviews = Review.objects.filter(author=request.user).order_by('-created_at')
    
    context = {
        'reviews': reviews,
    }
    return render(request, 'dashboard/client_reviews.html', context)


@login_required
def client_review_edit(request, review_id):
    """
    Modifier un avis
    URL: /dashboard/client/review/<int:review_id>/edit/
    Template: dashboard/client_review_edit.html
    """
    review = get_object_or_404(Review, id=review_id, author=request.user)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        if rating and comment:
            review.rating = int(rating)
            review.comment = comment
            review.save()
            messages.success(request, "Votre avis a été modifié avec succès.")
            return redirect('dashboard:client_reviews')
        else:
            messages.error(request, "Veuillez remplir tous les champs.")
    
    context = {
        'review': review,
    }
    return render(request, 'dashboard/client_review_edit.html', context)


@login_required
def client_review_delete(request, review_id):
    """
    Supprimer un avis
    URL: /dashboard/client/review/<int:review_id>/delete/
    """
    review = get_object_or_404(Review, id=review_id, author=request.user)
    
    if request.method == 'POST':
        review.delete()
        messages.success(request, "Votre avis a été supprimé.")
        return redirect('dashboard:client_reviews')
    
    return render(request, 'dashboard/client_review_delete.html', {'review': review})

@login_required
def client_messages(request):
    """
    Liste des conversations du client
    URL: /dashboard/client/messages/
    Template: dashboard/client_messages.html
    """
    conversations = Conversation.objects.filter(
        participants=request.user
    ).order_by('-updated_at')
    
    
    context = {
        'conversations': conversations,
    }
    return render(request, 'dashboard/client_messages.html', context)


@login_required
def client_profile(request):
    """
    Profil du client (redirection vers accounts:profile)
    """
    return redirect('accounts:profile')


@login_required
def client_profile_edit(request):
    """
    Modifier le profil du client (redirection vers accounts:edit_profile)
    """
    return redirect('accounts:edit_profile')


@login_required
def client_search(request):
    """
    Page de recherche rapide pour le client
    URL: /dashboard/client/search/
    Template: dashboard/client_search.html
    """
    quartier = request.GET.get('quartier', '')
    property_type = request.GET.get('property_type', '')
    budget_min = request.GET.get('budget_min', '')
    budget_max = request.GET.get('budget_max', '')
    
    properties = Property.objects.filter(is_approved=True, is_active=True)
    
    if quartier:
        properties = properties.filter(quartier__icontains=quartier)
    if property_type:
        properties = properties.filter(property_type=property_type)
    if budget_min:
        properties = properties.filter(price__gte=budget_min)
    if budget_max:
        properties = properties.filter(price__lte=budget_max)
    
    context = {
        'properties': properties,
        'quartier': quartier,
        'property_type': property_type,
        'budget_min': budget_min,
        'budget_max': budget_max,
    }
    return render(request, 'dashboard/client_search.html', context)


@login_required
def dashboard_redirect(request):
    """
    Redirige vers le dashboard approprié selon le rôle de l'utilisateur
    """
    user = request.user
    
    if user.is_superuser or user.is_staff:
        return redirect('dashboard:admin_dashboard')

    profile = UserProfile.objects.filter(user=user).first()
    if profile and profile.role == 'proprietaire':
        return redirect('dashboard:owner_dashboard')

    if OwnerVerification.objects.filter(user=user).exists():
        return redirect('dashboard:owner_dashboard')

    return redirect('dashboard:client_dashboard')



# ============================================
# DÉCORATEUR PROPRIÉTAIRE
# ============================================

def owner_required(view_func):
    """Décorateur pour restreindre aux propriétaires"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Veuillez vous connecter.")
            return redirect('accounts:login')
        
        profile = UserProfile.objects.filter(user=request.user).first()
        is_owner = (
            profile and profile.role == 'proprietaire'
        ) or OwnerVerification.objects.filter(user=request.user).exists()
        if not request.user.is_superuser and not is_owner:
            messages.error(request, "Accès réservé aux propriétaires.")
            return redirect('dashboard:client_dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================
# DASHBOARD PROPRIÉTAIRE PRINCIPAL
# ============================================

@login_required
@owner_required
def owner_dashboard(request):
    """
    Tableau de bord du propriétaire
    URL: /dashboard/owner/
    Template: dashboard/owner_dashboard.html
    """
    user = request.user
    
    # ===== STATISTIQUES =====
    # Annonces
    total_properties = Property.objects.filter(owner=user).count()
    active_properties = Property.objects.filter(owner=user, is_active=True, is_approved=True).count()
    pending_properties = Property.objects.filter(owner=user, is_approved=False).count()
    
    # Réservations
    total_bookings = Booking.objects.filter(property__owner=user).count()
    pending_bookings = Booking.objects.filter(property__owner=user, status='pending').count()
    confirmed_bookings = Booking.objects.filter(property__owner=user, status='confirmed').count()
    completed_bookings = Booking.objects.filter(property__owner=user, status='completed').count()
    
    # Revenus
    total_revenue = Booking.objects.filter(
        property__owner=user,
        status__in=['confirmed', 'completed']
    ).aggregate(total=Sum('property__price'))['total'] or 0
    
    # Avis
    properties_ids = Property.objects.filter(owner=user).values_list('id', flat=True)
    total_reviews = Review.objects.filter(property_id__in=properties_ids).count()
    avg_rating = Review.objects.filter(property_id__in=properties_ids).aggregate(
        avg=Avg('rating')
    )['avg'] or 0
    
    # ===== ANNONCES RÉCENTES =====
    recent_properties = Property.objects.filter(owner=user).order_by('-created_at')[:5]
    
    # ===== RÉSERVATIONS RÉCENTES =====
    recent_bookings = Booking.objects.filter(property__owner=user).order_by('-created_at')[:5]
    
    # ===== NOTIFICATIONS =====
    unread_notifications = Notification.objects.filter(user=user, is_read=False).count()
    recent_notifications = Notification.objects.filter(user=user).order_by('-created_at')[:5]
    
    # ===== STATUT DE VÉRIFICATION =====
    try:
        from accounts.models import OwnerVerification
        verification = OwnerVerification.objects.get(user=user)
        verification_status = verification.status
    except:
        verification_status = 'pending'
    
    context = {
        # Statistiques
        'total_properties': total_properties,
        'active_properties': active_properties,
        'pending_properties': pending_properties,
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
        'confirmed_bookings': confirmed_bookings,
        'completed_bookings': completed_bookings,
        'total_revenue': total_revenue,
        'total_reviews': total_reviews,
        'avg_rating': avg_rating,
        'verification_status': verification_status,
        
        # Listes
        'recent_properties': recent_properties,
        'recent_bookings': recent_bookings,
        'recent_notifications': recent_notifications,
        'unread_notifications': unread_notifications,
    }
    
    return render(request, 'dashboard/owner_dashboard.html', context)


# ============================================
# GESTION DES ANNONCES (PROPRIÉTAIRE)
# ============================================

@login_required
@owner_required
def owner_properties(request):
    """
    Liste des annonces du propriétaire
    URL: /dashboard/owner/properties/
    Template: dashboard/owner_properties.html
    """
    properties = Property.objects.filter(owner=request.user).order_by('-created_at')
    
    # Filtres
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        properties = properties.filter(is_active=True, is_approved=True)
    elif status_filter == 'pending':
        properties = properties.filter(is_approved=False)
    elif status_filter == 'inactive':
        properties = properties.filter(is_active=False, is_approved=True)
    
    search = request.GET.get('search')
    if search:
        properties = properties.filter(
            Q(title__icontains=search) |
            Q(quartier__icontains=search) |
            Q(address__icontains=search)
        )
    
    context = {
        'properties': properties,
        'status_filter': status_filter,
        'search': search,
    }
    return render(request, 'dashboard/owner_properties.html', context)


@login_required
@owner_required
def owner_property_create(request):
    """
    Créer une nouvelle annonce
    URL: /dashboard/owner/property/create/
    Template: dashboard/owner_property_form.html
    """
    if request.method == 'POST':
        # Récupération des données
        title = request.POST.get('title')
        description = request.POST.get('description')
        property_type = request.POST.get('property_type')
        price = request.POST.get('price')
        surface_area = request.POST.get('surface_area')
        quartier = request.POST.get('quartier')
        address = request.POST.get('address')
        number_rooms = request.POST.get('number_rooms')
        number_bathrooms = request.POST.get('number_bathrooms')
        
        # Équipements (checkboxes)
        furnished = request.POST.get('furnished') == 'on'
        has_kitchen = request.POST.get('has_kitchen') == 'on'
        has_parking = request.POST.get('has_parking') == 'on'
        has_security = request.POST.get('has_security') == 'on'
        has_wifi = request.POST.get('has_wifi') == 'on'
        has_air_conditioning = request.POST.get('has_air_conditioning') == 'on'
        has_balcony = request.POST.get('has_balcony') == 'on'
        
        # Images
        images = request.FILES.getlist('images')
        
        # Validation
        errors = []
        
        if not title:
            errors.append("Le titre est obligatoire.")
        if not description:
            errors.append("La description est obligatoire.")
        if not property_type:
            errors.append("Le type de logement est obligatoire.")
        if not price:
            errors.append("Le prix est obligatoire.")
        elif not price.isdigit() or int(price) <= 0:
            errors.append("Le prix doit être un nombre positif.")
        if not surface_area:
            errors.append("La surface est obligatoire.")
        elif not surface_area.isdigit() or int(surface_area) <= 0:
            errors.append("La surface doit être un nombre positif.")
        if not quartier:
            errors.append("Le quartier est obligatoire.")
        if not address:
            errors.append("L'adresse est obligatoire.")
        
        if errors:
            context = {
                'errors': errors,
                'title': title,
                'description': description,
                'property_type': property_type,
                'price': price,
                'surface_area': surface_area,
                'quartier': quartier,
                'address': address,
                'number_rooms': number_rooms,
                'number_bathrooms': number_bathrooms,
            }
            return render(request, 'dashboard/owner_property_form.html', context)
        
        # Création de l'annonce
        property = Property.objects.create(
            owner=request.user,
            title=title,
            description=description,
            property_type=property_type,
            price=price,
            surface_area=surface_area,
            quartier=quartier,
            address=address,
            number_rooms=number_rooms or 0,
            number_bathrooms=number_bathrooms or 0,
            furnished=furnished,
            has_kitchen=has_kitchen,
            has_parking=has_parking,
            has_security=has_security,
            has_wifi=has_wifi,
            has_air_conditioning=has_air_conditioning,
            has_balcony=has_balcony,
            is_approved=False,  # En attente de validation
            is_active=False,
        )
        
        # Sauvegarde des images
        for i, image in enumerate(images):
            PropertyImage.objects.create(
                property=property,
                image=image,
                is_main=(i == 0),
                order=i
            )
        
        # Notification à l'admin
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            Notification.objects.create(
                user=admin,
                type='new_property',
                title='Nouvelle annonce à valider',
                message=f"Le propriétaire {request.user.username} a publié une nouvelle annonce : {title}",
                link=f'/dashboard/admin/annonces/'
            )
        
        messages.success(request, "Votre annonce a été créée avec succès ! Elle est en attente de validation.")
        return redirect('dashboard:owner_properties')
    
    return render(request, 'dashboard/owner_property_form.html')


@login_required
@owner_required
def owner_property_edit(request, property_id):
    """
    Modifier une annonce
    URL: /dashboard/owner/property/<int:property_id>/edit/
    Template: dashboard/owner_property_form.html
    """
    property = get_object_or_404(Property, id=property_id, owner=request.user)
    
    if request.method == 'POST':
        # Mise à jour des données
        property.title = request.POST.get('title')
        property.description = request.POST.get('description')
        property.property_type = request.POST.get('property_type')
        property.price = request.POST.get('price')
        property.surface_area = request.POST.get('surface_area')
        property.quartier = request.POST.get('quartier')
        property.address = request.POST.get('address')
        property.number_rooms = request.POST.get('number_rooms') or 0
        property.number_bathrooms = request.POST.get('number_bathrooms') or 0
        
        # Équipements
        property.furnished = request.POST.get('furnished') == 'on'
        property.has_kitchen = request.POST.get('has_kitchen') == 'on'
        property.has_parking = request.POST.get('has_parking') == 'on'
        property.has_security = request.POST.get('has_security') == 'on'
        property.has_wifi = request.POST.get('has_wifi') == 'on'
        property.has_air_conditioning = request.POST.get('has_air_conditioning') == 'on'
        property.has_balcony = request.POST.get('has_balcony') == 'on'
        
        property.save()
        
        # Nouvelles images
        new_images = request.FILES.getlist('images')
        for i, image in enumerate(new_images):
            PropertyImage.objects.create(
                property=property,
                image=image,
                is_main=(i == 0 and not property.images.filter(is_main=True).exists()),
                order=property.images.count() + i
            )
        
        messages.success(request, "Votre annonce a été mise à jour avec succès.")
        return redirect('dashboard:owner_properties')
    
    context = {
        'property': property,
        'is_edit': True,
    }
    return render(request, 'dashboard/owner_property_form.html', context)


@login_required
@owner_required
def delete_property_image(request, image_id):
    """Supprimer une image d'une annonce appartenant au propriétaire connecté."""
    image = get_object_or_404(
        PropertyImage,
        id=image_id,
        property__owner=request.user,
    )
    property_id = image.property_id

    if request.method == 'POST':
        was_main = image.is_main
        image.delete()

        if was_main:
            next_image = PropertyImage.objects.filter(
                property_id=property_id,
            ).first()
            if next_image:
                next_image.is_main = True
                next_image.save(update_fields=['is_main'])

        messages.success(request, "L'image a été supprimée.")

    return redirect('dashboard:owner_property_edit', property_id=property_id)


@login_required
@owner_required
def owner_property_delete(request, property_id):
    """
    Supprimer une annonce
    URL: /dashboard/owner/property/<int:property_id>/delete/
    """
    property = get_object_or_404(Property, id=property_id, owner=request.user)
    
    if request.method == 'POST':
        title = property.title
        property.delete()
        messages.success(request, f"L'annonce '{title}' a été supprimée.")
        return redirect('dashboard:owner_properties')
    
    return render(request, 'dashboard/owner_property_delete.html', {'property': property})


@login_required
@owner_required
def owner_property_toggle_active(request, property_id):
    """
    Activer/Désactiver une annonce
    URL: /dashboard/owner/property/<int:property_id>/toggle/
    """
    property = get_object_or_404(Property, id=property_id, owner=request.user)
    
    if property.is_approved:
        property.is_active = not property.is_active
        property.save()
        
        status = "activée" if property.is_active else "désactivée"
        messages.success(request, f"L'annonce '{property.title}' a été {status}.")
    else:
        messages.error(request, "Cette annonce n'est pas encore validée par l'administrateur.")
    
    return redirect('dashboard:owner_properties')


# ============================================
# GESTION DES RÉSERVATIONS (PROPRIÉTAIRE)
# ============================================

@login_required
@owner_required
def owner_bookings(request):
    """
    Liste des réservations du propriétaire
    URL: /dashboard/owner/bookings/
    Template: dashboard/owner_bookings.html
    """
    bookings = Booking.objects.filter(property__owner=request.user).order_by('-created_at')
    
    # Filtres
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    context = {
        'bookings': bookings,
        'status_filter': status_filter,
    }
    return render(request, 'dashboard/owner_bookings.html', context)


@login_required
@owner_required
def owner_booking_detail(request, booking_id):
    """
    Détail d'une réservation
    URL: /dashboard/owner/booking/<int:booking_id>/
    Template: dashboard/owner_booking_detail.html
    """
    booking = get_object_or_404(Booking, id=booking_id, property__owner=request.user)
    
    context = {
        'booking': booking,
    }
    return render(request, 'dashboard/owner_booking_detail.html', context)


@login_required
@owner_required
def owner_booking_process(request, booking_id):
    """
    Accepter ou refuser une réservation
    URL: /dashboard/owner/booking/<int:booking_id>/process/
    """
    booking = get_object_or_404(Booking, id=booking_id, property__owner=request.user)
    
    if booking.status != 'pending':
        messages.warning(request, "Cette réservation a déjà été traitée.")
        return redirect('dashboard:owner_booking_detail', booking_id=booking.id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        message_owner = request.POST.get('message', '')
        
        if action == 'accept':
            booking.status = 'confirmed'
            booking.save()
            
            # Notification au client
            Notification.objects.create(
                user=booking.tenant,
                type='booking_confirmed',
                title='✅ Réservation confirmée',
                message=f"Votre réservation pour '{booking.property.title}' a été confirmée par le propriétaire.",
                link=f'/bookings/{booking.id}/'
            )
            
            messages.success(request, f"La réservation de {booking.tenant.username} a été acceptée.")
            
        elif action == 'reject':
            booking.status = 'refused'
            booking.save()
            
            # Notification au client
            Notification.objects.create(
                user=booking.tenant,
                type='booking_cancelled',
                title='❌ Réservation refusée',
                message=f"Votre réservation pour '{booking.property.title}' a été refusée par le propriétaire.",
                link=f'/bookings/{booking.id}/'
            )
            
            messages.info(request, f"La réservation de {booking.tenant.username} a été refusée.")
        
        return redirect('dashboard:owner_bookings')
    
    context = {
        'booking': booking,
    }
    return render(request, 'dashboard/owner_booking_process.html', context)


# ============================================
# GESTION DES AVIS (PROPRIÉTAIRE)
# ============================================

@login_required
@owner_required
def owner_reviews(request):
    """
    Liste des avis reçus par le propriétaire
    URL: /dashboard/owner/reviews/
    Template: dashboard/owner_reviews.html
    """
    properties_ids = Property.objects.filter(owner=request.user).values_list('id', flat=True)
    reviews = Review.objects.filter(property_id__in=properties_ids).order_by('-created_at')
    
    # Statistiques
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    total_reviews = reviews.count()
    
    # Répartition des notes
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[i] = reviews.filter(rating=i).count()
    
    context = {
        'reviews': reviews,
        'avg_rating': avg_rating,
        'total_reviews': total_reviews,
        'rating_distribution': rating_distribution,
    }
    return render(request, 'dashboard/owner_reviews.html', context)


# ============================================
# STATISTIQUES (PROPRIÉTAIRE)
# ============================================

@login_required
@owner_required
def owner_statistics(request):
    """
    Statistiques détaillées du propriétaire
    URL: /dashboard/owner/statistics/
    Template: dashboard/owner_statistics.html
    """
    user = request.user
    
    # Réservations par mois (6 derniers mois)
    bookings_by_month = []
    for i in range(5, -1, -1):
        month = timezone.now().month - i
        year = timezone.now().year
        if month <= 0:
            month += 12
            year -= 1
        
        start_date = timezone.datetime(year, month, 1)
        if month == 12:
            end_date = timezone.datetime(year + 1, 1, 1)
        else:
            end_date = timezone.datetime(year, month + 1, 1)
        
        count = Booking.objects.filter(
            owner=user,
            created_at__gte=start_date,
            created_at__lt=end_date
        ).count()
        
        revenue = Booking.objects.filter(
            property__owner=user,
            status__in=['confirmed', 'completed'],
            created_at__gte=start_date,
            created_at__lt=end_date
        ).aggregate(total=Sum('property__price'))['total'] or 0
        
        bookings_by_month.append({
            'month': start_date.strftime('%b %Y'),
            'count': count,
            'revenue': revenue,
        })
    
    # Top propriétés
    top_properties = Property.objects.filter(
        owner=user
    ).annotate(
        booking_count=Count('bookings')
    ).order_by('-booking_count')[:5]
    
    context = {
        'bookings_by_month': bookings_by_month,
        'top_properties': top_properties,
    }
    return render(request, 'dashboard/owner_statistics.html', context)


# ============================================
# STATUT DE VÉRIFICATION
# ============================================

@login_required
@owner_required
def owner_verification_status(request):
    """
    Statut de vérification du propriétaire
    URL: /dashboard/owner/verification/
    """
    try:
        from accounts.models import OwnerVerification
        verification = OwnerVerification.objects.get(user=request.user)
        status = verification.status
        notes = verification.admin_notes
        submitted_at = verification.submitted_at
        verified_at = verification.verified_at
    except:
        status = 'not_submitted'
        notes = ''
        submitted_at = None
        verified_at = None
    
    context = {
        'status': status,
        'notes': notes,
        'submitted_at': submitted_at,
        'verified_at': verified_at,
    }
    return render(request, 'dashboard/owner_verification_status.html', context)


# ============================================
# MESSAGES (PROPRIÉTAIRE)
# ============================================

@login_required
@owner_required
def owner_messages(request):
    """
    Liste des conversations du propriétaire
    URL: /dashboard/owner/messages/
    Template: dashboard/owner_messages.html
    """
    conversations = Conversation.objects.filter(
        participants=request.user
    ).order_by('-updated_at')
    
    context = {
        'conversations': conversations,
    }
    return render(request, 'dashboard/owner_messages.html', context)


# ============================================
# CONFIRMATION DE DISPONIBILITÉ (30 jours)
# ============================================

@login_required
@owner_required
def owner_confirm_availability(request):
    """
    Confirmer la disponibilité des annonces (tous les 30 jours)
    URL: /dashboard/owner/confirm-availability/
    """
    if request.method == 'POST':
        property_ids = request.POST.getlist('property_ids')
        
        for property_id in property_ids:
            try:
                property = Property.objects.get(id=property_id, owner=request.user)
                property.last_confirmation_date = timezone.now()
                property.confirmation_pending = False
                property.is_active = True
                property.save()
            except Property.DoesNotExist:
                pass
        
        messages.success(request, "Disponibilité confirmée pour les annonces sélectionnées.")
        return redirect('dashboard:owner_dashboard')
    
    # Annonces nécessitant une confirmation
    thirty_days_ago = timezone.now() - timedelta(days=30)
    properties_to_confirm = Property.objects.filter(
        owner=request.user,
        is_active=True,
        is_approved=True,
        last_confirmation_date__lt=thirty_days_ago
    )
   
    context = {
        'properties_to_confirm': properties_to_confirm,
    }
    return render(request, 'dashboard/owner_confirm_availability.html', context)

    # dashboard/views.py - AJOUTER CETTE FONCTION


@login_required
def owner_statistics(request):
    """
    Statistiques détaillées du propriétaire
    URL: /dashboard/proprietaire/statistiques/
    Template: dashboard/owner_statistics.html
    """
    user = request.user
    
    # ============================================
    # 1. STATISTIQUES GÉNÉRALES
    # ============================================
    
    # Annonces
    total_properties = Property.objects.filter(owner=user).count()
    active_properties = Property.objects.filter(owner=user, is_active=True, is_approved=True).count()
    pending_properties = Property.objects.filter(owner=user, is_approved=False).count()
    
    # Réservations
    total_bookings = Booking.objects.filter(property__owner=user).count()
    pending_bookings = Booking.objects.filter(property__owner=user, status='pending').count()
    confirmed_bookings = Booking.objects.filter(property__owner=user, status='confirmed').count()
    completed_bookings = Booking.objects.filter(property__owner=user, status='completed').count()
    cancelled_bookings = Booking.objects.filter(property__owner=user, status='cancelled').count()
    
    # Revenus
    total_revenue = Booking.objects.filter(
        property__owner=user,
        status__in=['confirmed', 'completed']
    ).aggregate(total=Sum('property__price'))['total'] or 0
    
    # Revenus du mois en cours
    current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0)
    monthly_revenue = Booking.objects.filter(
        property__owner=user,
        status__in=['confirmed', 'completed'],
        created_at__gte=current_month_start
    ).aggregate(total=Sum('property__price'))['total'] or 0
    
    # Avis
    properties_ids = Property.objects.filter(owner=user).values_list('id', flat=True)
    reviews = Review.objects.filter(property_id__in=properties_ids)
    total_reviews = reviews.count()
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Vues totales
    total_views = Property.objects.filter(owner=user).aggregate(
        total=Sum('views_count')
    )['total'] or 0
    
    # Taux d'occupation
    # (Réservations confirmées ou terminées / Total annonces actives)
    if active_properties > 0:
        occupied_properties = Property.objects.filter(
            owner=user,
            is_active=True,
            is_approved=True,
            bookings__status__in=['confirmed', 'completed']
        ).distinct().count()
        occupancy_rate = round((occupied_properties / active_properties) * 100, 1)
    else:
        occupancy_rate = 0
    
    # ============================================
    # 2. ÉVOLUTION MENSUELLE (6 derniers mois)
    # ============================================
    
    monthly_data = []
    for i in range(5, -1, -1):
        # Calculer le mois
        month = timezone.now().month - i
        year = timezone.now().year
        
        if month <= 0:
            month += 12
            year -= 1
        
        # Premier jour du mois
        start_date = timezone.datetime(year, month, 1)
        
        # Dernier jour du mois
        last_day = monthrange(year, month)[1]
        end_date = timezone.datetime(year, month, last_day, 23, 59, 59)
        
        # Réservations du mois
        bookings_count = Booking.objects.filter(
            property__owner=user,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Revenus du mois
        revenue = Booking.objects.filter(
            property__owner=user,
            status__in=['confirmed', 'completed'],
            created_at__gte=start_date,
            created_at__lte=end_date
        ).aggregate(total=Sum('property__price'))['total'] or 0
        
        # Vues du mois (approximatif)
        views = Property.objects.filter(
            owner=user,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).aggregate(total=Sum('views_count'))['total'] or 0
        
        # Nom du mois en français
        month_names = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 
                       'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
        
        monthly_data.append({
            'month': month_names[month - 1],
            'year': year,
            'full_label': f"{month_names[month - 1]} {year}",
            'bookings': bookings_count,
            'revenue': float(revenue),
            'views': views,
        })
    
    # ============================================
    # 3. TOP ANNONCES (par réservations)
    # ============================================
    
    top_properties = Property.objects.filter(
        owner=user
    ).annotate(
        booking_count=Count('bookings'),
        total_revenue=Sum('bookings__property__price', filter=Q(bookings__status__in=['confirmed', 'completed'])),
        review_count=Count('reviews'),
        avg_rating=Avg('reviews__rating'),
    ).order_by('-booking_count')[:5]
    
    top_properties_data = []
    for prop in top_properties:
        top_properties_data.append({
            'id': prop.id,
            'title': prop.title,
            'quartier': prop.quartier,
            'price': int(prop.price),
            'views': prop.views_count,
            'bookings': prop.booking_count or 0,
            'revenue': float(prop.total_revenue or 0),
            'reviews': prop.review_count or 0,
            'rating': round(prop.avg_rating or 0, 1),
        })
    
    # ============================================
    # 4. RÉPARTITION DES STATUTS DE RÉSERVATION
    # ============================================
    
    booking_statuses = {
        'pending': pending_bookings,
        'confirmed': confirmed_bookings,
        'completed': completed_bookings,
        'cancelled': cancelled_bookings,
    }
    
    # ============================================
    # 5. RÉPARTITION DES NOTES (Avis)
    # ============================================
    
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[i] = reviews.filter(rating=i).count()
    
    # ============================================
    # 6. RÉPARTITION PAR QUARTIER
    # ============================================
    
    properties_by_quartier = Property.objects.filter(
        owner=user
    ).values('quartier').annotate(
        count=Count('id'),
        total_bookings=Count('bookings'),
        total_revenue=Sum('bookings__property__price', filter=Q(bookings__status__in=['confirmed', 'completed'])),
    ).order_by('-count')[:10]

    properties_by_quartier_data = [
        {
            'quartier': item['quartier'],
            'count': item['count'],
        }
        for item in properties_by_quartier
    ]
    
    # ============================================
    # 7. RÉPARTITION PAR TYPE DE LOGEMENT
    # ============================================
    
    properties_by_type = Property.objects.filter(
        owner=user
    ).values('property_type').annotate(
        count=Count('id'),
        total_bookings=Count('bookings'),
    ).order_by('-count')
    
    # Traduire les types
    type_names = {
        'appartement': 'Appartement',
        'maison': 'Maison',
        'studio': 'Studio',
        'duplex': 'Duplex',
        'villa': 'Villa',
        'chambre': 'Chambre',
    }
    
    properties_by_type_data = []
    for item in properties_by_type:
        properties_by_type_data.append({
            'type': type_names.get(item['property_type'], item['property_type']),
            'count': item['count'],
            'bookings': item['total_bookings'],
        })
    
    # ============================================
    # 8. TAUX DE CONVERSION
    # ============================================
    
    # Vues → Réservations
    if total_views > 0:
        conversion_rate = round((total_bookings / total_views) * 100, 2)
    else:
        conversion_rate = 0
    
    context = {
        # Statistiques générales
        'total_properties': total_properties,
        'active_properties': active_properties,
        'pending_properties': pending_properties,
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
        'confirmed_bookings': confirmed_bookings,
        'completed_bookings': completed_bookings,
        'cancelled_bookings': cancelled_bookings,
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'total_reviews': total_reviews,
        'avg_rating': round(avg_rating, 1),
        'total_views': total_views,
        'occupancy_rate': occupancy_rate,
        'conversion_rate': conversion_rate,
        
        # Données pour graphiques
        'monthly_data_json': json.dumps(monthly_data),
        'top_properties_json': json.dumps(top_properties_data),
        'booking_statuses_json': json.dumps(booking_statuses),
        'rating_distribution_json': json.dumps(rating_distribution),
        'properties_by_type_json': json.dumps(properties_by_type_data),
        'properties_by_quartier_json': json.dumps(properties_by_quartier_data),
        'monthly_data': monthly_data,
        'booking_statuses_data': booking_statuses,
        'rating_distribution_data': rating_distribution,
        'properties_by_type_data': properties_by_type_data,
        'properties_by_quartier_data': properties_by_quartier_data,
        
        # Listes
        'top_properties': top_properties_data,
        'properties_by_quartier': properties_by_quartier,
        'properties_by_type': properties_by_type_data,
        'rating_distribution': rating_distribution,
        'booking_statuses': booking_statuses,
    }
    
    return render(request, 'dashboard/owner_statistics.html', context)

    # dashboard/views.py - AJOUTER CETTE FONCTION


@login_required
def admin_statistics(request):
    """
    Statistiques détaillées pour l'administrateur
    URL: /dashboard/admin/statistiques/
    Template: dashboard/admin_statistics.html
    """
    # Vérifier que l'utilisateur est admin
    if not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Vous n'avez pas les droits d'administrateur.")
        return redirect('home')
    
    # ============================================
    # 1. STATISTIQUES GÉNÉRALES
    # ============================================
    
    # Utilisateurs
    total_users = User.objects.count()
    total_clients = User.objects.filter(is_superuser=False, is_staff=False).count()
    total_proprietaires = User.objects.filter(is_superuser=False, is_staff=False).count()  # À adapter avec votre champ role
    total_admins = User.objects.filter(Q(is_superuser=True) | Q(is_staff=True)).count()
    
    # Utilisateurs actifs (derniers 7 jours)
    week_ago = timezone.now() - timedelta(days=7)
    active_users = User.objects.filter(last_login__gte=week_ago).count()
    
    # Nouveaux utilisateurs ce mois
    current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0)
    new_users_month = User.objects.filter(date_joined__gte=current_month_start).count()
    
    # Annonces
    total_properties = Property.objects.count()
    approved_properties = Property.objects.filter(is_approved=True).count()
    pending_properties = Property.objects.filter(is_approved=False).count()
    active_properties = Property.objects.filter(is_approved=True, is_active=True).count()
    inactive_properties = Property.objects.filter(is_approved=True, is_active=False).count()
    
    # Réservations
    total_bookings = Booking.objects.count()
    pending_bookings = Booking.objects.filter(status='pending').count()
    confirmed_bookings = Booking.objects.filter(status='confirmed').count()
    completed_bookings = Booking.objects.filter(status='completed').count()
    cancelled_bookings = Booking.objects.filter(status='cancelled').count()
    refused_bookings = Booking.objects.filter(status='refused').count()
    
    # Revenus totaux (somme de toutes les réservations confirmées/terminées)
    total_revenue = Booking.objects.filter(
        status__in=['confirmed', 'completed']
    ).aggregate(total=Sum('property__price'))['total'] or 0
    
    # Revenus du mois
    monthly_revenue = Booking.objects.filter(
        status__in=['confirmed', 'completed'],
        created_at__gte=current_month_start
    ).aggregate(total=Sum('property__price'))['total'] or 0
    
    # Avis
    total_reviews = Review.objects.count()
    avg_rating = Review.objects.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Vérifications
    total_verifications = OwnerVerification.objects.count()
    pending_verifications = OwnerVerification.objects.filter(status='pending').count()
    approved_verifications = OwnerVerification.objects.filter(status='approved').count()
    rejected_verifications = OwnerVerification.objects.filter(status='rejected').count()
    
    # Signalements
    total_incidents = IncidentReport.objects.count()
    pending_incidents = IncidentReport.objects.filter(status='pending').count()
    resolved_incidents = IncidentReport.objects.filter(status='resolved').count()
    
    # Vues totales
    total_views = Property.objects.aggregate(total=Sum('views_count'))['total'] or 0
    
    # ============================================
    # 2. ÉVOLUTION MENSUELLE (6 derniers mois)
    # ============================================
    
    monthly_data = []
    month_names = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 
                   'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
    
    for i in range(5, -1, -1):
        month = timezone.now().month - i
        year = timezone.now().year
        
        if month <= 0:
            month += 12
            year -= 1
        
        start_date = timezone.datetime(year, month, 1)
        last_day = monthrange(year, month)[1]
        end_date = timezone.datetime(year, month, last_day, 23, 59, 59)
        
        # Nouveaux utilisateurs
        users_count = User.objects.filter(
            date_joined__gte=start_date,
            date_joined__lte=end_date
        ).count()
        
        # Nouvelles annonces
        properties_count = Property.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Réservations
        bookings_count = Booking.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Revenus
        revenue = Booking.objects.filter(
            status__in=['confirmed', 'completed'],
            created_at__gte=start_date,
            created_at__lte=end_date
        ).aggregate(total=Sum('property__price'))['total'] or 0
        
        monthly_data.append({
            'month': month_names[month - 1],
            'year': year,
            'full_label': f"{month_names[month - 1]} {year}",
            'users': users_count,
            'properties': properties_count,
            'bookings': bookings_count,
            'revenue': float(revenue),
        })
    
    # ============================================
    # 3. TOP QUARTIERS
    # ============================================
    
    top_quartiers = Property.objects.filter(
        is_approved=True
    ).values('quartier').annotate(
        count=Count('id'),
        total_bookings=Count('bookings'),
        total_revenue=Sum('bookings__property__price', filter=Q(bookings__status__in=['confirmed', 'completed']))
    ).order_by('-count')[:10]
    
    top_quartiers_data = []
    for q in top_quartiers:
        top_quartiers_data.append({
            'quartier': q['quartier'],
            'count': q['count'],
            'bookings': q['total_bookings'],
            'revenue': float(q['total_revenue'] or 0),
        })
    
    # ============================================
    # 4. TOP PROPRIÉTAIRES
    # ============================================
    
    top_owners = User.objects.filter(
        properties__isnull=False
    ).annotate(
        property_count=Count('properties', distinct=True),
        booking_count=Count('properties__bookings', distinct=True),
        total_revenue=Sum('properties__bookings__property__price', 
                         filter=Q(properties__bookings__status__in=['confirmed', 'completed'])),
    ).order_by('-property_count')[:10]
    
    top_owners_data = []
    for owner in top_owners:
        top_owners_data.append({
            'id': owner.id,
            'username': owner.username,
            'email': owner.email,
            'properties': owner.property_count,
            'bookings': owner.booking_count,
            'revenue': float(owner.total_revenue or 0),
        })
    
    # ============================================
    # 5. TOP ANNONCES
    # ============================================
    
    top_properties = Property.objects.filter(
        is_approved=True
    ).annotate(
        booking_count=Count('bookings'),
        review_count=Count('reviews'),
        avg_rating=Avg('reviews__rating'),
    ).order_by('-views_count')[:10]
    
    top_properties_data = []
    for prop in top_properties:
        top_properties_data.append({
            'id': prop.id,
            'title': prop.title,
            'quartier': prop.quartier,
            'owner': prop.owner.username,
            'price': int(prop.price),
            'views': prop.views_count,
            'bookings': prop.booking_count,
            'rating': round(prop.avg_rating or 0, 1),
        })
    
    # ============================================
    # 6. RÉPARTITION DES RÔLES
    # ============================================
    
    roles_data = {
        'clients': total_clients,
        'proprietaires': total_proprietaires,
        'admins': total_admins,
    }
    
    # ============================================
    # 7. STATUTS DES ANNONCES
    # ============================================
    
    properties_status_data = {
        'approved': approved_properties,
        'pending': pending_properties,
        'active': active_properties,
        'inactive': inactive_properties,
    }
    
    # ============================================
    # 8. STATUTS DES RÉSERVATIONS
    # ============================================
    
    bookings_status_data = {
        'pending': pending_bookings,
        'confirmed': confirmed_bookings,
        'completed': completed_bookings,
        'cancelled': cancelled_bookings,
        'refused': refused_bookings,
    }
    
    # ============================================
    # 9. STATUTS DES VÉRIFICATIONS
    # ============================================
    
    verifications_status_data = {
        'pending': pending_verifications,
        'approved': approved_verifications,
        'rejected': rejected_verifications,
    }
    
    # ============================================
    # 10. RÉPARTITION DES NOTES
    # ============================================
    
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[i] = Review.objects.filter(rating=i).count()
    
    # ============================================
    # 11. TYPES DE LOGEMENTS
    # ============================================
    
    type_names = {
        'appartement': 'Appartement',
        'maison': 'Maison',
        'studio': 'Studio',
        'duplex': 'Duplex',
        'villa': 'Villa',
        'chambre': 'Chambre',
    }
    
    properties_by_type = Property.objects.filter(
        is_approved=True
    ).values('property_type').annotate(
        count=Count('id'),
        total_bookings=Count('bookings'),
    ).order_by('-count')
    
    properties_by_type_data = []
    for item in properties_by_type:
        properties_by_type_data.append({
            'type': type_names.get(item['property_type'], item['property_type']),
            'count': item['count'],
            'bookings': item['total_bookings'],
        })
    
    # ============================================
    # CONTEXTE
    # ============================================
    
    context = {
        # Statistiques générales
        'total_users': total_users,
        'total_clients': total_clients,
        'total_proprietaires': total_proprietaires,
        'total_admins': total_admins,
        'active_users': active_users,
        'new_users_month': new_users_month,
        
        'total_properties': total_properties,
        'approved_properties': approved_properties,
        'pending_properties': pending_properties,
        'active_properties': active_properties,
        'inactive_properties': inactive_properties,
        
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
        'confirmed_bookings': confirmed_bookings,
        'completed_bookings': completed_bookings,
        'cancelled_bookings': cancelled_bookings,
        'refused_bookings': refused_bookings,
        
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        
        'total_reviews': total_reviews,
        'avg_rating': round(avg_rating, 1),
        
        'total_verifications': total_verifications,
        'pending_verifications': pending_verifications,
        'approved_verifications': approved_verifications,
        'rejected_verifications': rejected_verifications,
        
        'total_incidents': total_incidents,
        'pending_incidents': pending_incidents,
        'resolved_incidents': resolved_incidents,
        
        'total_views': total_views,
        
        # Données pour graphiques (JSON)
        'monthly_data_json': json.dumps(monthly_data),
        'top_quartiers_json': json.dumps(top_quartiers_data),
        'top_owners_json': json.dumps(top_owners_data),
        'roles_data_json': json.dumps(roles_data),
        'properties_status_json': json.dumps(properties_status_data),
        'bookings_status_json': json.dumps(bookings_status_data),
        'verifications_status_json': json.dumps(verifications_status_data),
        'rating_distribution_json': json.dumps(rating_distribution),
        'properties_by_type_json': json.dumps(properties_by_type_data),
        
        # Listes pour tableaux
        'top_quartiers': top_quartiers_data,
        'top_owners': top_owners_data,
        'top_properties': top_properties_data,
        'rating_distribution': rating_distribution,
        'properties_by_type': properties_by_type_data,
    }
    
    return render(request, 'dashboard/admin_statistics.html', context)

   


# ============================================
# DÉCORATEUR ADMIN
# ============================================

def admin_required(view_func):
    """Décorateur pour restreindre aux administrateurs"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Veuillez vous connecter.")
            return redirect('accounts:login')
        
        if not request.user.is_superuser and not request.user.is_staff:
            messages.error(request, "Vous n'avez pas les droits d'administrateur.")
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================
# LISTE DES UTILISATEURS
# ============================================

@login_required
@admin_required
def users_list(request):
    """
    Liste des utilisateurs avec filtres et recherche
    URL: /dashboard/admin/utilisateurs/
    Template: dashboard/users_list.html
    """
    # ===== REQUÊTE DE BASE =====
    users = User.objects.all().select_related('profile').order_by('-date_joined')
    
    # ===== RECHERCHE =====
    search = request.GET.get('search', '').strip()
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(profile__phone_number__icontains=search)
        )
    
    # ===== FILTRES =====
    role_filter = request.GET.get('role', '')
    if role_filter == 'client':
        users = users.filter(is_superuser=False, is_staff=False)
    elif role_filter == 'proprietaire':
        users = users.filter(properties__isnull=False).distinct()
    elif role_filter == 'admin':
        users = users.filter(Q(is_superuser=True) | Q(is_staff=True))
    
    # Statut actif/inactif
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # Vérification
    verification_filter = request.GET.get('verification', '')
    if verification_filter == 'verified':
        users = users.filter(profile__is_verified=True)
    elif verification_filter == 'pending':
        users = users.filter(profile__verification_status='pending')
    elif verification_filter == 'rejected':
        users = users.filter(profile__verification_status='rejected')
    
    # ===== STATISTIQUES =====
    total_users = User.objects.count()
    total_clients = User.objects.filter(is_superuser=False, is_staff=False).count()
    total_owners = User.objects.filter(properties__isnull=False).distinct().count()
    total_admins = User.objects.filter(Q(is_superuser=True) | Q(is_staff=True)).count()
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = User.objects.filter(is_active=False).count()
    
    # ===== PAGINATION =====
    paginator = Paginator(users, 20)  # 20 utilisateurs par page
    page = request.GET.get('page', 1)
    
    try:
        users_page = paginator.page(page)
    except:
        users_page = paginator.page(1)
    
    context = {
        'users': users_page,
        'search': search,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'verification_filter': verification_filter,
        'total_users': total_users,
        'total_clients': total_clients,
        'total_owners': total_owners,
        'total_admins': total_admins,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'paginator': paginator,
    }
    return render(request, 'dashboard/users_list.html', context)


# ============================================
# DÉTAIL D'UN UTILISATEUR
# ============================================

@login_required
@admin_required
def user_detail(request, user_id):
    """
    Détail d'un utilisateur
    URL: /dashboard/admin/utilisateur/<int:user_id>/
    Template: dashboard/user_detail.html
    """
    user_obj = get_object_or_404(User, id=user_id)
    
    # Statistiques de l'utilisateur
    if user_obj.is_superuser or user_obj.is_staff:
        user_type = 'admin'
    elif user_obj.properties.exists():
        user_type = 'proprietaire'
    else:
        user_type = 'client'
    
    # Propriétés (si propriétaire)
    properties = Property.objects.filter(owner=user_obj).order_by('-created_at')
    total_properties = properties.count()
    
    # Réservations (si client)
    bookings = Booking.objects.filter(tenant=user_obj).order_by('-created_at')
    total_bookings = bookings.count()
    
    # Réservations en tant que propriétaire
    owner_bookings = Booking.objects.filter(property__owner=user_obj).order_by('-created_at')
    total_owner_bookings = owner_bookings.count()
    
    # Revenus (si propriétaire)
    total_revenue = Booking.objects.filter(
        property__owner=user_obj,
        status__in=['confirmed', 'completed']
    ).aggregate(total=Sum('property__price'))['total'] or 0
    
    # Avis reçus
    properties_ids = properties.values_list('id', flat=True)
    reviews = Review.objects.filter(property_id__in=properties_ids)
    total_reviews = reviews.count()
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Vérification
    try:
        verification = OwnerVerification.objects.get(user=user_obj)
    except OwnerVerification.DoesNotExist:
        verification = None
    
    # Actions récentes
    actions = AdminActionLog.objects.filter(target_user=user_obj)[:10]
    
    context = {
        'user_obj': user_obj,
        'user_type': user_type,
        'properties': properties[:10],
        'total_properties': total_properties,
        'bookings': bookings[:10],
        'total_bookings': total_bookings,
        'owner_bookings': owner_bookings[:10],
        'total_owner_bookings': total_owner_bookings,
        'total_revenue': total_revenue,
        'reviews': reviews[:10],
        'total_reviews': total_reviews,
        'avg_rating': round(avg_rating, 1),
        'verification': verification,
        'actions': actions,
    }
    return render(request, 'dashboard/user_detail.html', context)


# ============================================
# ACTIVER/DÉSACTIVER UN UTILISATEUR
# ============================================

@login_required
@admin_required
def user_toggle_active(request, user_id):
    """
    Activer/Désactiver un utilisateur
    URL: /dashboard/admin/utilisateur/<int:user_id>/activer/
    """
    user_obj = get_object_or_404(User, id=user_id)
    
    # Empêcher la désactivation de soi-même
    if user_obj == request.user:
        messages.error(request, "Vous ne pouvez pas désactiver votre propre compte.")
        return redirect('dashboard:users_list')
    
    # Empêcher la désactivation des superutilisateurs
    if user_obj.is_superuser and not request.user.is_superuser:
        messages.error(request, "Vous ne pouvez pas désactiver un superutilisateur.")
        return redirect('dashboard:users_list')
    
    user_obj.is_active = not user_obj.is_active
    user_obj.save()
    
    status = "activé" if user_obj.is_active else "désactivé"
    messages.success(request, f"L'utilisateur {user_obj.username} a été {status}.")
    
    # Journalisation
    AdminActionLog.objects.create(
        admin=request.user,
        action_type='user_activate' if user_obj.is_active else 'user_deactivate',
        description=f"Utilisateur {user_obj.username} {status}",
        target_user=user_obj
    )
    
    # Notification à l'utilisateur
    Notification.objects.create(
        user=user_obj,
        type='system',
        title=f'Compte {status}',
        message=f"Votre compte a été {status} par un administrateur.",
        link='/'
    )
    
    return redirect('dashboard:users_list')


# ============================================
# SUPPRIMER UN UTILISATEUR
# ============================================

@login_required
@admin_required
def user_delete(request, user_id):
    """
    Supprimer un utilisateur
    URL: /dashboard/admin/utilisateur/<int:user_id>/supprimer/
    """
    user_obj = get_object_or_404(User, id=user_id)
    
    # Empêcher la suppression de soi-même
    if user_obj == request.user:
        messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
        return redirect('dashboard:users_list')
    
    # Empêcher la suppression des superutilisateurs
    if user_obj.is_superuser and not request.user.is_superuser:
        messages.error(request, "Vous ne pouvez pas supprimer un superutilisateur.")
        return redirect('dashboard:users_list')
    
    if request.method == 'POST':
        username = user_obj.username
        email = user_obj.email
        
        # Suppression
        user_obj.delete()
        
        # Journalisation
        AdminActionLog.objects.create(
            admin=request.user,
            action_type='user_delete',
            description=f"Utilisateur {username} ({email}) supprimé",
            target_user=None
        )
        
        messages.success(request, f"L'utilisateur {username} a été supprimé définitivement.")
        return redirect('dashboard:users_list')
    
    context = {
        'user_obj': user_obj,
    }
    return render(request, 'dashboard/user_delete.html', context)


# ============================================
# VÉRIFIER UN PROPRIÉTAIRE
# ============================================

@login_required
@admin_required
def user_verify(request, user_id):
    """
    Vérifier un propriétaire
    URL: /dashboard/admin/utilisateur/<int:user_id>/verifier/
    Template: dashboard/user_verify.html
    """
    user_obj = get_object_or_404(User, id=user_id)
    
    try:
        verification = OwnerVerification.objects.get(user=user_obj)
    except OwnerVerification.DoesNotExist:
        messages.error(request, "Aucune demande de vérification trouvée pour cet utilisateur.")
        return redirect('dashboard:user_detail', user_id=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            verification.status = 'approved'
            verification.verified_at = timezone.now()
            verification.admin_notes = notes
            verification.save()
            
            # Mettre à jour le profil
            if hasattr(user_obj, 'profile'):
                user_obj.profile.is_verified = True
                user_obj.profile.verification_status = 'approved'
                user_obj.profile.save()
            
            # Notification
            Notification.objects.create(
                user=user_obj,
                type='owner_verification',
                title='✅ Vérification approuvée',
                message="Félicitations ! Votre compte propriétaire a été vérifié avec succès.",
                link='/dashboard/proprietaire/'
            )
            
            # Journalisation
            AdminActionLog.objects.create(
                admin=request.user,
                action_type='user_verify',
                description=f"Propriétaire {user_obj.username} vérifié",
                target_user=user_obj
            )
            
            messages.success(request, f"Le propriétaire {user_obj.username} a été vérifié.")
            
        elif action == 'reject':
            verification.status = 'rejected'
            verification.verified_at = timezone.now()
            verification.admin_notes = notes
            verification.save()
            
            # Mettre à jour le profil
            if hasattr(user_obj, 'profile'):
                user_obj.profile.is_verified = False
                user_obj.profile.verification_status = 'rejected'
                user_obj.profile.save()
            
            # Notification
            Notification.objects.create(
                user=user_obj,
                type='owner_verification',
                title='❌ Vérification rejetée',
                message=f"Votre demande de vérification a été rejetée. Raison : {notes if notes else 'Documents non conformes'}",
                link='/accounts/verify-owner/'
            )
            
            # Journalisation
            AdminActionLog.objects.create(
                admin=request.user,
                action_type='user_reject',
                description=f"Propriétaire {user_obj.username} rejeté",
                target_user=user_obj
            )
            
            messages.info(request, f"La vérification de {user_obj.username} a été rejetée.")
        
        return redirect('dashboard:user_detail', user_id=user_id)
    
    context = {
        'user_obj': user_obj,
        'verification': verification,
    }
    return render(request, 'dashboard/user_verify.html', context)


# ============================================
# STATISTIQUES PAR UTILISATEUR (AJAX)
# ============================================

@login_required
@admin_required
def user_stats_ajax(request, user_id):
    """
    Statistiques d'un utilisateur (AJAX)
    URL: /dashboard/admin/utilisateur/<int:user_id>/stats/
    """
    user_obj = get_object_or_404(User, id=user_id)
    
    # Propriétés
    properties_count = Property.objects.filter(owner=user_obj).count()
    
    # Réservations
    bookings_count = Booking.objects.filter(tenant=user_obj).count()
    owner_bookings_count = Booking.objects.filter(property__owner=user_obj).count()
    
    # Revenus
    revenue = Booking.objects.filter(
        property__owner=user_obj,
        status__in=['confirmed', 'completed']
    ).aggregate(total=Sum('property__price'))['total'] or 0
    
    # Avis
    properties_ids = Property.objects.filter(owner=user_obj).values_list('id', flat=True)
    reviews_count = Review.objects.filter(property_id__in=properties_ids).count()
    avg_rating = Review.objects.filter(property_id__in=properties_ids).aggregate(
        avg=Avg('rating')
    )['avg'] or 0
    
    return JsonResponse({
        'properties': properties_count,
        'bookings': bookings_count,
        'owner_bookings': owner_bookings_count,
        'revenue': float(revenue),
        'reviews': reviews_count,
        'avg_rating': round(avg_rating, 1),
    })


# ============================================
# ACTIONS EN MASSE
# ============================================

@login_required
@admin_required
def users_bulk_action(request):
    """
    Actions en masse sur les utilisateurs
    URL: /dashboard/admin/utilisateurs/bulk/
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        user_ids = request.POST.getlist('user_ids')
        
        if not user_ids:
            messages.warning(request, "Aucun utilisateur sélectionné.")
            return redirect('dashboard:users_list')
        
        users = User.objects.filter(id__in=user_ids).exclude(id=request.user.id)
        
        if action == 'activate':
            users.update(is_active=True)
            count = users.count()
            messages.success(request, f"{count} utilisateur(s) activé(s).")
            
        elif action == 'deactivate':
            users = users.exclude(is_superuser=True)
            users.update(is_active=False)
            count = users.count()
            messages.success(request, f"{count} utilisateur(s) désactivé(s).")
            
        elif action == 'delete':
            users = users.exclude(is_superuser=True)
            count = users.count()
            users.delete()
            messages.success(request, f"{count} utilisateur(s) supprimé(s).")
        
        # Journalisation
        AdminActionLog.objects.create(
            admin=request.user,
            action_type='user_activate' if action == 'activate' else 'user_deactivate',
            description=f"Action en masse : {action} sur {len(user_ids)} utilisateur(s)",
        )
    
    return redirect('dashboard:users_list')


# ============================================
# EXPORT DES UTILISATEURS
# ============================================

@login_required
@admin_required
def users_export(request):
    """
    Exporter la liste des utilisateurs en CSV
    URL: /dashboard/admin/utilisateurs/export/
    """
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="utilisateurs_habiora.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Username', 'Email', 'Prénom', 'Nom', 'Téléphone', 'Rôle', 'Actif', 'Vérifié', 'Date inscription'])
    
    users = User.objects.all().select_related('profile')
    
    for user in users:
        role = 'Admin' if user.is_superuser else ('Propriétaire' if user.properties.exists() else 'Client')
        phone = user.profile.phone_number if hasattr(user, 'profile') else ''
        verified = user.profile.is_verified if hasattr(user, 'profile') else False
        
        writer.writerow([
            user.id,
            user.username,
            user.email,
            user.first_name,
            user.last_name,
            phone,
            role,
            'Oui' if user.is_active else 'Non',
            'Oui' if verified else 'Non',
            user.date_joined.strftime('%d/%m/%Y %H:%M'),
        ])
    
    return response

@staff_member_required
def verification_list(request):
    qs = VerificationRequest.objects.select_related('user', 'processed_by')
    
    # Filtres
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)
    
    q = request.GET.get('q')
    if q:
        qs = qs.filter(
            Q(user__email__icontains=q) |
            Q(user__username__icontains=q) |
            Q(id__icontains=q)
        )
    
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'dashboard/admin/list.html', {
        'page_obj': page,
        'status': status,
        'q': q,
    })


@staff_member_required
def verification_detail(request, pk):
    req = get_object_or_404(
        VerificationRequest.objects.select_related('user', 'processed_by'),
        pk=pk
    )
    return render(request, 'dashboard/admin/detail.html', {
        'req': req,
        'logs': req.logs.select_related('actor').all(),
    })


@staff_member_required
def verification_traiter(request, pk):
    """Vue principale de traitement"""
    req = get_object_or_404(
        VerificationRequest.objects.select_related('user'),
        pk=pk
    )
    
    if req.is_final:
        messages.warning(request, "Cette demande est déjà traitée.")
        return redirect('dashboard:verification_detail', pk=pk)
    
    approve_form = ApproveForm(prefix='approve')
    reject_form = RejectForm(prefix='reject')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'start_review':
            VerificationService.start_review(req, request.user)
            messages.info(request, "Demande marquée en cours d'examen.")
            return redirect('dashboard:verification_traiter', pk=pk)
        
        if action == 'approve':
            approve_form = ApproveForm(request.POST, prefix='approve')
            if approve_form.is_valid():
                VerificationService.approve(
                    req, request.user,
                    notes=approve_form.cleaned_data['notes']
                )
                messages.success(request, "Demande approuvée. Utilisateur notifié.")
                return redirect('dashboard:verification_list')
        
        if action == 'reject':
            reject_form = RejectForm(request.POST, prefix='reject')
            if reject_form.is_valid():
                VerificationService.reject(
                    req, request.user,
                    reason=reject_form.cleaned_data['reason'],
                    notes=reject_form.cleaned_data['notes']
                )
                messages.success(request, "Demande rejetée. Utilisateur notifié.")
                return redirect('dashboard:verification_list')
    
    return render(request, 'dashboard/admin/traiter.html', {
        'req': req,
        'approve_form': approve_form,
        'reject_form': reject_form,
        'logs': req.logs.select_related('actor').all(),
    })
# Create your views here.
