import secrets
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from .models import EmailChangeRequest, LoginHistory, UserSession
from django.db import transaction
from .models import OwnerRequest

class EmailService:

    @staticmethod
    def _send(subject, template, context, to_email):
        html = render_to_string(template, context)
        send_mail(
            subject=subject,
            message='',
            html_message=html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=True,
        )

    @classmethod
    def send_email_change_confirmation(cls, req, request):
        link = request.build_absolute_uri(
            reverse('accounts:confirm_email_change', args=[req.token])
        )
        cls._send(
            "Confirmez votre nouvel email",
            'accounts/emails/email_change.html',
            {'user': req.user, 'link': link},
            req.new_email
        )

    @classmethod
    def send_password_changed(cls, user):
        cls._send(
            "Mot de passe modifié",
            'accounts/emails/password_changed.html',
            {'user': user},
            user.email
        )

    @classmethod
    def send_welcome(cls, user):
        cls._send(
            "Bienvenue",
            'accounts/emails/welcome.html',
            {'user': user},
            user.email
        )


class EmailChangeService:

    @staticmethod
    def create_request(user, new_email):
        EmailChangeRequest.objects.filter(
            user=user, confirmed_at__isnull=True
        ).update(confirmed_at=timezone.now())
        return EmailChangeRequest.objects.create(
            user=user,
            new_email=new_email,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + timedelta(hours=24)
        )

    @staticmethod
    def confirm(token):
        try:
            req = EmailChangeRequest.objects.get(token=token)
        except EmailChangeRequest.DoesNotExist:
            raise ValueError("Lien invalide.")
        if not req.is_valid():
            raise ValueError("Ce lien a expiré ou a déjà été utilisé.")
        user = req.user
        user.email = req.new_email
        user.is_verified = True
        user.save(update_fields=['email', 'is_verified'])
        req.confirmed_at = timezone.now()
        req.save(update_fields=['confirmed_at'])
        return user


class LoginHistoryService:

    @staticmethod
    def log(request, user=None, success=True, reason='', email=''):
        LoginHistory.objects.create(
            user=user,
            email_attempted=email or (user.email if user else ''),
            ip_address=LoginHistoryService._get_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            success=success,
            failure_reason=reason,
        )

    @staticmethod
    def _get_ip(request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class SessionService:

    @staticmethod
    def track(request, user):
        if not request.session.session_key:
            request.session.save()
        key = request.session.session_key
        UserSession.objects.update_or_create(
            session_key=key,
            defaults={
                'user': user,
                'ip_address': LoginHistoryService._get_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                'is_active': True,
            }
        )

    @staticmethod
    def list_for_user(user):
        return user.sessions.filter(is_active=True).order_by('-last_activity')

    @staticmethod
    def revoke(user, session_id):
        try:
            s = user.sessions.get(id=session_id)
        except UserSession.DoesNotExist:
            raise ValueError("Session introuvable.")
        s.is_active = False
        s.save(update_fields=['is_active'])

    @staticmethod
    def revoke_all(user, except_session_key=None):
        qs = user.sessions.filter(is_active=True)
        if except_session_key:
            qs = qs.exclude(session_key=except_session_key)
        return qs.update(is_active=False)


class AccountService:

    @staticmethod
    def anonymize(user, reason=''):
        user.email = f"deleted_{user.uuid}@anonymized.local"
        user.username = f"deleted_{str(user.uuid)[:8]}"
        user.first_name = ''
        user.last_name = ''
        user.phone = ''
        user.is_active = False
        user.is_owner = False
        user.save()
        p = user.profile
        p.avatar = None
        p.bio = ''
        p.location = ''
        p.website = ''
        p.save()
        UserSession.objects.filter(user=user).update(is_active=False)

        # accounts/services.py — AJOUTER
class OwnerRequestService:

    @staticmethod
    def create_or_update(user, data):
        """Crée ou met à jour la demande d'un utilisateur"""
        req, _ = OwnerRequest.objects.get_or_create(
            user=user,
            defaults={'status': 'pending'}
        )
        if req.is_final and req.status == 'approved':
            raise ValueError("Vous êtes déjà propriétaire.")

        for field, value in data.items():
            setattr(req, field, value)

        # Repasser en pending si c'était rejeté
        if req.status == 'rejected':
            req.status = 'pending'
            req.rejection_reason = ''

        req.save()
        return req

    @staticmethod
    @transaction.atomic
    def approve(req, admin_user):
        """Valider → l'utilisateur devient propriétaire"""
        if req.is_final and req.status == 'approved':
            raise ValueError("Déjà approuvée.")

        req.status = 'approved'
        req.processed_by = admin_user
        req.processed_at = timezone.now()
        req.save()

        # LE POINT CLÉ : promotion de l'utilisateur
        user = req.user
        user.is_owner = True
        if user.role == 'client':
            user.role = 'both'
        elif user.role not in ('owner', 'both', 'admin'):
            user.role = 'owner'
        user.save(update_fields=['is_owner', 'role'])

        return req

    @staticmethod
    @transaction.atomic
    def reject(req, admin_user, reason):
        if not reason.strip():
            raise ValueError("Motif obligatoire.")
        req.status = 'rejected'
        req.processed_by = admin_user
        req.processed_at = timezone.now()
        req.rejection_reason = reason
        req.save()
        return req