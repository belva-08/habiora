from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):

    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire.")
        if not username:
            raise ValueError("Le nom d'utilisateur est obligatoire.")
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('role', 'owner')
        return self.create_user(email, username, password, **extra_fields)

    def owners(self):
        return self.filter(role__in=['owner', 'both'], is_active=True)

    def clients(self):
        return self.filter(role__in=['client', 'both'], is_active=True)