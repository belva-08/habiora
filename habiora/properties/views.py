from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count, Avg
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from .models import Property, PropertyImage, PropertyFeature
from bookings.models import Booking
from reviews.models import Review, IncidentReport
from notifications.models import Notification


# ============================================
# LISTE DES ANNONCES (PAGE PUBLIQUE)
# ============================================

def property_list(request):
    """
    Liste des annonces avec filtres et recherche
    URL: /properties/
    Template: properties/property_list.html
    """
    # ===== REQUÊTE DE BASE =====
    properties = Property.objects.filter(
        is_approved=True,
        is_active=True
    ).select_related('owner').prefetch_related('images')
    
    # ===== RECHERCHE =====
    search_query = request.GET.get('q', '').strip()
    if search_query:
        properties = properties.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(quartier__icontains=search_query) |
            Q(address__icontains=search_query) |
            Q(owner__username__icontains=search_query)
        )
    
    # ===== FILTRES =====
    # Quartier
    quartier = request.GET.get('quartier', '')
    if quartier:
        properties = properties.filter(quartier__iexact=quartier)
    
    # Type de logement
    property_type = request.GET.get('property_type', '')
    if property_type:
        properties = properties.filter(property_type=property_type)
    
    # Budget
    budget_min = request.GET.get('budget_min', '')
    budget_max = request.GET.get('budget_max', '')
    if budget_min and budget_min.isdigit():
        properties = properties.filter(price__gte=budget_min)
    if budget_max and budget_max.isdigit():
        properties = properties.filter(price__lte=budget_max)
    
    # Surface
    surface_min = request.GET.get('surface_min', '')
    surface_max = request.GET.get('surface_max', '')
    if surface_min and surface_min.isdigit():
        properties = properties.filter(surface_area__gte=surface_min)
    if surface_max and surface_max.isdigit():
        properties = properties.filter(surface_area__lte=surface_max)
    
    # Pièces
    rooms = request.GET.get('rooms', '')
    if rooms and rooms.isdigit():
        properties = properties.filter(number_rooms__gte=rooms)
    
    # Équipements
    furnished = request.GET.get('furnished')
    if furnished == 'on':
        properties = properties.filter(furnished=True)
    
    has_parking = request.GET.get('has_parking')
    if has_parking == 'on':
        properties = properties.filter(has_parking=True)
    
    has_wifi = request.GET.get('has_wifi')
    if has_wifi == 'on':
        properties = properties.filter(has_wifi=True)
    
    has_security = request.GET.get('has_security')
    if has_security == 'on':
        properties = properties.filter(has_security=True)
    
    has_air_conditioning = request.GET.get('has_air_conditioning')
    if has_air_conditioning == 'on':
        properties = properties.filter(has_air_conditioning=True)
    
    # ===== TRI =====
    sort_by = request.GET.get('sort', 'newest')
    
    if sort_by == 'newest':
        properties = properties.order_by('-created_at')
    elif sort_by == 'oldest':
        properties = properties.order_by('created_at')
    elif sort_by == 'price_asc':
        properties = properties.order_by('price')
    elif sort_by == 'price_desc':
        properties = properties.order_by('-price')
    elif sort_by == 'popular':
        properties = properties.order_by('-views_count')
    elif sort_by == 'rating':
        properties = properties.annotate(
            avg_rating=Avg('reviews__rating')
        ).order_by('-avg_rating')
    
    # ===== PAGINATION =====
    paginator = Paginator(properties, 12)  # 12 annonces par page
    page = request.GET.get('page', 1)
    
    try:
        properties_page = paginator.page(page)
    except PageNotAnInteger:
        properties_page = paginator.page(1)
    except EmptyPage:
        properties_page = paginator.page(paginator.num_pages)
    
    # ===== QUARTIERS POPULAIRES (pour les filtres) =====
    quartiers = Property.objects.filter(
        is_approved=True, 
        is_active=True
    ).values('quartier').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # ===== TYPES DE LOGEMENT (pour les filtres) =====
    property_types = Property.objects.filter(
        is_approved=True, 
        is_active=True
    ).values('property_type').annotate(
        count=Count('id')
    ).order_by('property_type')
    
    # ===== STATISTIQUES =====
    total_properties = Property.objects.filter(is_approved=True, is_active=True).count()
    
    context = {
        'properties': properties_page,
        'search_query': search_query,
        'quartier': quartier,
        'property_type': property_type,
        'budget_min': budget_min,
        'budget_max': budget_max,
        'surface_min': surface_min,
        'surface_max': surface_max,
        'rooms': rooms,
        'furnished': furnished,
        'has_parking': has_parking,
        'has_wifi': has_wifi,
        'has_security': has_security,
        'has_air_conditioning': has_air_conditioning,
        'sort_by': sort_by,
        'quartiers': quartiers,
        'property_types': property_types,
        'total_properties': total_properties,
        'paginator': paginator,
    }
    
    return render(request, 'properties/property_list.html', context)


# ============================================
# DÉTAIL D'UNE ANNONCE
# ============================================

def property_detail(request, property_id):
    """
    Détail d'une annonce
    URL: /properties/<int:property_id>/
    Template: properties/property_detail.html
    """
    property = get_object_or_404(
        Property.objects.select_related('owner').prefetch_related('images'),
        id=property_id,
        is_approved=True
    )
    
    # Incrémenter le compteur de vues
    property.views_count += 1
    property.save(update_fields=['views_count'])
    
    # ===== ANNONCES SIMILAIRES =====
    similar_properties = Property.objects.filter(
        is_approved=True,
        is_active=True,
        quartier=property.quartier
    ).exclude(id=property.id)[:4]
    
    # ===== AVIS =====
    reviews = Review.objects.filter(property=property).order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # ===== VÉRIFIER SI L'UTILISATEUR A DÉJÀ RÉSERVÉ =====
    has_booked = False
    can_review = False
    
    if request.user.is_authenticated:
        has_booked = Booking.objects.filter(
            property=property,
            client=request.user,
            status__in=['confirmed', 'completed']
        ).exists()
        
        can_review = Booking.objects.filter(
            property=property,
            client=request.user,
            status='completed'
        ).exists() and not Review.objects.filter(
            property=property,
            user=request.user
        ).exists()
    
    # ===== DISPONIBILITÉ (30 jours) =====
    thirty_days_ago = timezone.now() - timedelta(days=30)
    is_available = property.is_active and property.last_confirmation_date > thirty_days_ago
    
    context = {
        'property': property,
        'similar_properties': similar_properties,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'reviews_count': reviews.count(),
        'has_booked': has_booked,
        'can_review': can_review,
        'is_available': is_available,
    }
    
    return render(request, 'properties/property_detail.html', context)


# ============================================
# ANNONCES PAR QUARTIER (API / Vue Carte)
# ============================================

def property_map(request):
    """
    Vue carte des annonces
    URL: /properties/map/
    Template: properties/property_map.html
    """
    properties = Property.objects.filter(
        is_approved=True,
        is_active=True,
        latitude__isnull=False,
        longitude__isnull=False
    ).select_related('owner').prefetch_related('images')
    
    # Filtres pour la carte
    quartier = request.GET.get('quartier', '')
    if quartier:
        properties = properties.filter(quartier__iexact=quartier)
    
    property_type = request.GET.get('property_type', '')
    if property_type:
        properties = properties.filter(property_type=property_type)
    
    # Convertir pour la carte
    properties_data = []
    for prop in properties:
        properties_data.append({
            'id': prop.id,
            'title': prop.title,
            'latitude': float(prop.latitude),
            'longitude': float(prop.longitude),
            'address': prop.address,
            'quartier': prop.quartier,
            'price': int(prop.price),
            'image': prop.images.first().image.url if prop.images.exists() else None,
            'url': f'/properties/{prop.id}/'
        })
    
    context = {
        'properties': properties_data,
        'center_lat': 3.8480,   # Yaoundé
        'center_lng': 11.5021,
    }
    
    return render(request, 'properties/property_map.html', context)


# ============================================
# RECHERCHE AJAX (pour autocomplétion)
# ============================================

def property_search_ajax(request):
    """
    Recherche AJAX pour autocomplétion
    URL: /properties/search-ajax/
    """
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    properties = Property.objects.filter(
        is_approved=True,
        is_active=True,
        Q(title__icontains=query) |
        Q(quartier__icontains=query) |
        Q(address__icontains=query)
    )[:10]
    
    results = []
    for prop in properties:
        results.append({
            'id': prop.id,
            'title': prop.title,
            'quartier': prop.quartier,
            'price': int(prop.price),
            'url': f'/properties/{prop.id}/'
        })
    
    return JsonResponse(results, safe=False)


# ============================================
# TOGGLE FAVORI (si vous avez un modèle Favoris)
# ============================================

@login_required
def toggle_favorite(request, property_id):
    """
    Ajouter/Retirer des favoris
    URL: /properties/<int:property_id>/favorite/
    """
    property = get_object_or_404(Property, id=property_id, is_approved=True)
    
    # À adapter selon votre modèle Favoris
    # try:
    #     from favorites.models import Favorite
    #     favorite, created = Favorite.objects.get_or_create(
    #         user=request.user,
    #         property=property
    #     )
    #     if not created:
    #         favorite.delete()
    #         is_favorite = False
    #     else:
    #         is_favorite = True
    # except:
    #     is_favorite = False
    
    # Pour l'instant, simple toggle (à adapter)
    is_favorite = False
    
    if request.GET.get('ajax'):
        return JsonResponse({'is_favorite': is_favorite})
    
    return redirect('properties:detail', property_id=property_id)


# ============================================
# SIGNALER UNE ANNONCE
# ============================================

@login_required
def report_property(request, property_id):
    """
    Signaler une annonce
    URL: /properties/<int:property_id>/report/
    """
    property = get_object_or_404(Property, id=property_id, is_approved=True)
    
    if request.method == 'POST':
        incident_type = request.POST.get('incident_type')
        description = request.POST.get('description')
        
        if not incident_type or not description:
            messages.error(request, "Veuillez remplir tous les champs.")
            return render(request, 'properties/property_report.html', {'property': property})
        
        IncidentReport.objects.create(
            property=property,
            reported_by=request.user,
            incident_type=incident_type,
            description=description,
            status='pending'
        )
        
        # Notification à l'admin
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            Notification.objects.create(
                user=admin,
                type='incident_report',
                title='Nouveau signalement',
                message=f"Un signalement a été déposé pour l'annonce '{property.title}' par {request.user.username}",
                link=f'/dashboard/admin/signalements/'
            )
        
        messages.success(request, "Votre signalement a été envoyé avec succès. Nous allons l'examiner.")
        return redirect('properties:detail', property_id=property.id)
    
    context = {
        'property': property,
    }
    return render(request, 'properties/property_report.html', context)
# Create your views here.
