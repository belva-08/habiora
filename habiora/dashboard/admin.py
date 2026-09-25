from django.contrib import admin
from .models import VerificationRequest, VerificationLog


class VerificationLogInline(admin.TabularInline):
    model = VerificationLog
    extra = 0
    readonly_fields = ('actor', 'action', 'old_status', 'new_status', 'notes', 'created_at')


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'request_type', 'status', 'created_at', 'processed_by')
    list_filter = ('status', 'request_type', 'created_at')
    search_fields = ('user__email', 'user__username', 'id')
    readonly_fields = ('uuid', 'created_at', 'updated_at', 'processed_at')
    inlines = [VerificationLogInline]
    actions = ['mark_in_review']
    
    @admin.action(description="Marquer en cours d'examen")
    def mark_in_review(self, request, queryset):
        from .services import VerificationService
        for req in queryset.filter(status='pending'):
            VerificationService.start_review(req, request.user)
        self.message_user(request, f"{queryset.count()} demande(s) mise(s) à jour.")
# Register your models here.
