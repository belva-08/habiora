from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),


    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    path('verify-owner/', views.verify_owner, name='verify_owner'),

    path('password-reset/', views.password_reset, name='password_reset'),

    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    path('verify-owner/', views.verify_owner, name='verify_owner'),
    
    path('password-reset/', views.password_reset, name='password_reset'),
    
    # ===== SUPPRESSION DE COMPTE =====
    path('delete/', views.delete_account, name='delete_account'),
    path('deactivate/', views.deactivate_account, name='deactivate_account'),
    path('delete/confirm/', views.delete_account_confirm, name='delete_account_confirm'),
    path('export-data/', views.export_data, name='export_data'),
    # Authentification
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Profil
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Vérification propriétaire
    path('verify-owner/', views.verify_owner, name='verify_owner'),
    path('verification-status/', views.verification_status, name='verification_status'),
    
    # Suppression de compte
    path('delete/', views.delete_account, name='delete_account'),
    path('deactivate/', views.deactivate_account, name='deactivate_account'),
    path('delete/confirm/', views.delete_account_confirm, name='delete_account_confirm'),
    path('export-data/', views.export_data, name='export_data'),
    
    # Réinitialisation mot de passe
    path('password-reset/', views.password_reset, name='password_reset'),
    
    # ===== SUPPRESSION DE COMPTE =====
    path('delete/', views.delete_account, name='delete_account'),
    path('delete/confirm-final/', views.delete_account_confirm_final, name='delete_account_confirm_final'),
    path('delete/verify-password/', views.verify_delete_password, name='verify_delete_password'),
    path('delete/cancel/', views.cancel_deletion, name='cancel_deletion'),
    path('delete/export/', views.export_data_before_delete, name='export_data_before_delete'),
    path('deactivate/', views.deactivate_account, name='deactivate_account'),
    path('delete/confirm/', views.delete_account_confirm, name='delete_account_confirm'),
    path('export-data/', views.export_data, name='export_data'),
    # ===== AUTHENTIFICATION =====
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # ===== PROFIL =====
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # ===== VÉRIFICATION PROPRIÉTAIRE =====
    path('verify-owner/', views.verify_owner, name='verify_owner'),
    path('verification-status/', views.verification_status, name='verification_status'),
    
    # ===== SUPPRESSION DE COMPTE =====
    # Étape1 : Page initiale avec options
    path('delete/', views.delete_account, name='delete_account'),
    
    # Étape 2 : Confirmation finale
    path('delete/confirm-final/', views.delete_account_confirm_final, name='delete_account_confirm_final'),
    
    # Vérification mot de passe (AJAX)
    path('delete/verify-password/', views.verify_delete_password, name='verify_delete_password'),
    
    # Annuler la suppression
    path('delete/cancel/', views.cancel_deletion, name='cancel_deletion'),
    
    # Export des données
    path('delete/export/', views.export_data_before_delete, name='export_data_before_delete'),
    
    # Désactivation (alternative)
    path('deactivate/', views.deactivate_account, name='deactivate_account'),
    
    # ===== RÉINITIALISATION MOT DE PASSE =====
    path('password-reset/', views.password_reset, name='password_reset'),

    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('redirect/', views.redirect_after_login, name='redirect_after_login'),

    # Reset password (Django natif)
    path('password/reset/',
         auth_views.PasswordResetView.as_view(
             template_name='accounts/auth/password_reset.html',
             email_template_name='accounts/emails/password_reset.html',
             success_url='/accounts/password/reset/done/'
         ), name='password_reset'),
    path('password/reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/auth/password_reset_done.html'
         ), name='password_reset_done'),
    path('password/reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/auth/password_reset_confirm.html',
             success_url='/accounts/password/reset/complete/'
         ), name='password_reset_confirm'),
    path('password/reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/auth/password_reset_complete.html'
         ), name='password_reset_complete'),

    # Profil
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/owner/', views.owner_profile_edit, name='owner_profile_edit'),
    path('profile/password/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    path('profile/email/', views.email_change_request, name='email_change'),
    path('profile/email/confirm/<str:token>/', views.confirm_email_change, name='confirm_email_change'),
    path('profile/preferences/', views.preferences_view, name='preferences'),
    path('profile/sessions/', views.sessions_view, name='sessions'),
    path('profile/sessions/<int:session_id>/revoke/', views.revoke_session, name='revoke_session'),
    path('profile/sessions/revoke-all/', views.revoke_all_sessions, name='revoke_all_sessions'),
    path('profile/delete/', views.delete_account, name='delete_account'),

    # Devenir propriétaire
    path('become-owner/', views.become_owner, name='become_owner'),
    # Côté propriétaire
    path('owner/request/', views.owner_request_form, name='owner_request_form'),
    path('owner/request/status/', views.owner_request_status, name='owner_request_status'),

    # Côté admin
    path('admin/owner-requests/', views.admin_owner_requests, name='admin_owner_requests'),
    path('admin/owner-requests/<int:pk>/', views.admin_owner_request_detail, name='admin_owner_request_detail'),
]
# accounts/urls.py