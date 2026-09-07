from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # ===== REDIRECTION =====
    path('', views.dashboard_redirect, name='dashboard_redirect'),
    
    # ===== DASHBOARD ADMIN =====
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/statistiques/', views.admin_statistics, name='admin_statistics'),
    
    # ===== DASHBOARD CLIENT =====
    path('client/', views.client_dashboard, name='client_dashboard'),
    path('client/recherche/', views.client_search, name='client_search'),
    path('client/reservations/', views.client_bookings, name='client_bookings'),
    path('client/reservation/<int:booking_id>/', views.client_booking_detail, name='client_booking_detail'),
    path('client/reservation/<int:booking_id>/annuler/', views.client_booking_cancel, name='client_booking_cancel'),
    path('client/favoris/', views.client_favorites, name='client_favorites'),
    path('client/avis/', views.client_reviews, name='client_reviews'),
    path('client/avis/<int:review_id>/modifier/', views.client_review_edit, name='client_review_edit'),
    path('client/avis/<int:review_id>/supprimer/', views.client_review_delete, name='client_review_delete'),
    path('client/messages/', views.client_messages, name='client_messages'),
    path('client/profil/', views.client_profile, name='client_profile'),
    path('client/profil/modifier/', views.client_profile_edit, name='client_profile_edit'),
    
    # ===== DASHBOARD PROPRIÉTAIRE =====
    path('proprietaire/', views.owner_dashboard, name='owner_dashboard'),
    path('proprietaire/statistiques/', views.owner_statistics, name='owner_statistics'),
    path('proprietaire/verification/', views.owner_verification_status, name='owner_verification_status'),
    path('proprietaire/messages/', views.owner_messages, name='owner_messages'),
    path('proprietaire/confirmer-disponibilite/', views.owner_confirm_availability, name='owner_confirm_availability'),
    
    # ===== ANNONCES (Propriétaire) =====
    path('proprietaire/annonces/', views.owner_properties, name='owner_properties'),
    path('proprietaire/annonce/creer/', views.owner_property_create, name='owner_property_create'),
    path('proprietaire/annonce/<int:property_id>/modifier/', views.owner_property_edit, name='owner_property_edit'),
    path('proprietaire/annonce/<int:property_id>/supprimer/', views.owner_property_delete, name='owner_property_delete'),
    path('proprietaire/annonce/<int:property_id>/activer/', views.owner_property_toggle_active, name='owner_property_toggle_active'),
    
    # ===== RÉSERVATIONS (Propriétaire) =====
    path('proprietaire/reservations/', views.owner_bookings, name='owner_bookings'),
    path('proprietaire/reservation/<int:booking_id>/', views.owner_booking_detail, name='owner_booking_detail'),
    path('proprietaire/reservation/<int:booking_id>/traiter/', views.owner_booking_process, name='owner_booking_process'),
    
    # ===== AVIS (Propriétaire) =====
    path('proprietaire/avis/', views.owner_reviews, name='owner_reviews'),
    
    # ===== GESTION DES UTILISATEURS (Admin) =====
    path('admin/utilisateurs/', views.users_list, name='users_list'),
    path('admin/utilisateur/<int:user_id>/activer/', views.user_toggle_active, name='user_toggle_active'),
    path('admin/utilisateur/<int:user_id>/supprimer/', views.user_delete, name='user_delete'),
    
    # ===== GESTION DES ANNONCES (Admin) =====
    path('admin/annonces/', views.properties_list, name='properties_list'),
    path('admin/annonce/<int:property_id>/valider/', views.property_validate, name='property_validate'),
    path('admin/annonce/<int:property_id>/supprimer/', views.property_delete, name='property_delete'),
    
    # ===== VÉRIFICATIONS (Admin) =====
    path('admin/verifications/', views.verifications_list, name='verifications_list'),
    path('admin/verification/<int:verification_id>/traiter/', views.verification_process, name='verification_process'),
    
    # ===== SIGNALEMENTS (Admin) =====
    path('admin/signalements/', views.incidents_list, name='incidents_list'),
    path('admin/signalement/<int:incident_id>/traiter/', views.incident_process, name='incident_process'),
    
    # ===== NOTIFICATIONS =====
    path('notifications/', views.admin_notifications, name='admin_notifications'),
    path('notifications/marquer-toutes-lues/', views.mark_all_read, name='mark_all_read'),
    path('notifications/check/', views.check_notifications, name='check_notifications'),
]