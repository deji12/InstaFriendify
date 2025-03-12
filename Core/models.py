from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid

class CustomUserManager(BaseUserManager):
    def create_user(self, email, username=None, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        if not username:
            raise ValueError('Superuser must have a username.')
        if not email:
            raise ValueError('Superuser must have an email.')

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)  # Superusers should be active by default

        return self.create_user(email, username=username, password=password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(unique=True, max_length=255, null=True, blank=True)
    email = models.EmailField(unique=True, help_text="The user's unique email address.")
    first_name = models.CharField(max_length=30, default='', null=True, blank=True, help_text="The user's first name.")
    last_name = models.CharField(max_length=30, default='', null=True, blank=True, help_text="The user's last name.")
    
    max_close_friends_allocation = models.IntegerField(default=0, help_text="The maximum number of followers that this user can add to close friends list")
    current_allocation = models.IntegerField(default=0, help_text="The current number of space that this user has allocated to close friends")

    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False, help_text="Indicates whether the user has all admin permissions. Defaults to False.")
    is_active = models.BooleanField(default=False, help_text="Indicates whether the user account is active. Defaults to False and user needs to verify email on signup before it can be set to True.")
    date_joined = models.DateTimeField(auto_now_add=True, help_text="The date and time when the user joined.")

    def __str__(self):
        return self.username

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']  # No

class PasswordResetCode(models.Model):
    user = models.ForeignKey(User, on_delete = models.CASCADE)
    reset_id = models.UUIDField(default=uuid.uuid4, unique=True,editable=False)
    created_when = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'Password reset for {self.user.username} at {self.created_when}'