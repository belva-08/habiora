from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def owner_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_owner:
            raise PermissionDenied("Accès réservé aux propriétaires.")
        return view_func(request, *args, **kwargs)
    return wrapper


def client_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role not in ('client', 'both', 'admin'):
            raise PermissionDenied("Accès réservé aux clients.")
        return view_func(request, *args, **kwargs)
    return wrapper