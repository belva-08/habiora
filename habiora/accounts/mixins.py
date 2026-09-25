from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class OwnerRequiredMixin(LoginRequiredMixin):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_owner:
            raise PermissionDenied("Accès réservé aux propriétaires.")
        return super().dispatch(request, *args, **kwargs)


class ClientRequiredMixin(LoginRequiredMixin):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in ('client', 'both', 'admin'):
            raise PermissionDenied("Accès réservé aux clients.")
        return super().dispatch(request, *args, **kwargs)