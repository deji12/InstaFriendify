from .models import User

VERIFICATION_CODE_REQUIRED_FOR_ACCOUNT = 'Enter the verification code sent to your email or phone number'
TWO_FACTOR_REQUIRED_FOR_ACCOUNT = 'Two-factor authentication is required. Please enter the code sent to your email or phone number'
INSTAGRAM_ACCOUNT_CREATION_MODE = '2fa-code-required-on-account-creation'
INSTAGRAM_ACCOUNT_UPDATE_MODE = 'update-instagram-account'
TWO_FACTOR_REQUIRED_ON_ACCOUNT_UPDATE = '2fa-code-required-on-account-update'

UNKNOWN_ERROR = 'Please enter a valid security code and try again'
INVALID_CREDENTIALS = 'Incorrect username or password. Please try again.'


def authenticate(username, password):
    try:
        user = User.objects.get(username=username)
        if user.check_password(password):
            return user
        return None
    except User.DoesNotExist:
        return None