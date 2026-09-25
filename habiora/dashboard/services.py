from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from .models import VerificationRequest, VerificationLog


class VerificationService:
    """Logique de traitement des demandes de vérification"""
    
    @staticmethod
    def start_review(request_obj, actor):
        """Marquer comme en cours d'examen"""
        if request_obj.is_final:
            raise ValueError("Cette demande est déjà traitée.")
        
        old = request_obj.status
        request_obj.status = 'in_review'
        request_obj.save(update_fields=['status', 'updated_at'])
        
        VerificationLog.objects.create(
            request=request_obj,
            actor=actor,
            action='start_review',
            old_status=old,
            new_status='in_review',
        )
        return request_obj
    
    @staticmethod
    @transaction.atomic
    def approve(request_obj, actor, notes=''):
        """Approuver la demande"""
        if request_obj.is_final:
            raise ValueError("Cette demande est déjà traitée.")
        
        old = request_obj.status
        request_obj.status = 'approved'
        request_obj.processed_by = actor
        request_obj.processed_at = timezone.now()
        request_obj.admin_notes = notes
        request_obj.save()
        
        VerificationLog.objects.create(
            request=request_obj,
            actor=actor,
            action='approve',
            old_status=old,
            new_status='approved',
            notes=notes,
        )
        
        # Marquer l'utilisateur comme vérifié
        user = request_obj.user
        user.is_verified = True
        user.save(update_fields=['is_verified'])
        
        VerificationService._notify(request_obj, 'approved')
        return request_obj
    
    @staticmethod
    @transaction.atomic
    def reject(request_obj, actor, reason, notes=''):
        """Rejeter la demande"""
        if request_obj.is_final:
            raise ValueError("Cette demande est déjà traitée.")
        
        if not reason.strip():
            raise ValueError("Le motif de rejet est obligatoire.")
        
        old = request_obj.status
        request_obj.status = 'rejected'
        request_obj.processed_by = actor
        request_obj.processed_at = timezone.now()
        request_obj.rejection_reason = reason
        request_obj.admin_notes = notes
        request_obj.save()
        
        VerificationLog.objects.create(
            request=request_obj,
            actor=actor,
            action='reject',
            old_status=old,
            new_status='rejected',
            notes=reason,
        )
        
        VerificationService._notify(request_obj, 'rejected')
        return request_obj
    
    @staticmethod
    def cancel(request_obj, actor):
        old = request_obj.status
        request_obj.status = 'cancelled'
        request_obj.save(update_fields=['status', 'updated_at'])
        VerificationLog.objects.create(
            request=request_obj, actor=actor,
            action='cancel', old_status=old, new_status='cancelled',
        )
        return request_obj
    
    @staticmethod
    def _notify(request_obj, action):
        """Envoi d'email à l'utilisateur"""
        template = f'dashboard/admin/verification/emails/{action}.html'
        subject = "Votre demande a été approuvée" if action == 'approved' \
                  else "Votre demande a été rejetée"
        
        html = render_to_string(template, {'req': request_obj})
        send_mail(
            subject=subject,
            message='',
            html_message=html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request_obj.user.email],
            fail_silently=True,
        )