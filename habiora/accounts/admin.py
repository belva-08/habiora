from django.contrib import admin
from .models import Profile, UserSession, LoginHistory, EmailChangeRequest
from .models import OwnerRequest

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'language', 'company_name', 'updated_at')
    search_fields = ('user__email', 'user__username', 'company_name')


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'created_at', 'last_activity', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('user__email', 'ip_address')


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_attempted', 'ip_address', 'success', 'created_at')
    list_filter = ('success',)
    search_fields = ('user__email', 'email_attempted', 'ip_address')


@admin.register(EmailChangeRequest)
class EmailChangeRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'new_email', 'created_at', 'expires_at', 'confirmed_at')
    search_fields = ('user__email', 'new_email')

    # accounts/admin.py — AJOUTER

@admin.register(OwnerRequest)
class OwnerRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'status', 'created_at', 'processed_by')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'city', 'company_name')
    readonly_fields = ('created_at', 'updated_at', 'processed_at')
    actions = ['approve_requests', 'reject_requests']

    @admin.action(description="✅ Approuver les demandes sélectionnées")
    def approve_requests(self, request, queryset):
        from .services import OwnerRequestService
        for req in queryset.filter(status__in=['pending', 'in_review']):
            try:
                OwnerRequestService.approve(req, request.user)
            except ValueError:
                pass
        self.message_user(request, f"{queryset.count()} demande(s) traitée(s).")

    @admin.action(description="❌ Rejeter les demandes sélectionnées")
    def reject_requests(self, request, queryset):
        from .services import OwnerRequestService
        for req in queryset.filter(status__in=['pending', 'in_review']):
            try:
                OwnerRequestService.reject(req, request.user, "Rejeté en masse par admin.")
            except ValueError:
                pass
        self.message_user(request, f"{queryset.count()} demande(s) rejetée(s).")
# Register your models here.
