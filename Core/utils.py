from .models import User

def authenticate(username, password):
    try:
        user = User.objects.get(username=username)
        if user.check_password(password):
            return user
        return None
    except User.DoesNotExist:
        return None