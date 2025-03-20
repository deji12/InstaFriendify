from .models import User

VERIFICATION_CODE_REQUIRED_FOR_ACCOUNT = 'Inserisci il codice di verifica inviato alla tua email o al tuo numero di telefono'
TWO_FACTOR_REQUIRED_FOR_ACCOUNT = 'È richiesta l\'autenticazione a due fattori. Inserisci il codice inviato alla tua email o al tuo numero di telefono'
INSTAGRAM_ACCOUNT_CREATION_MODE = 'codice-2fa-richiesto-per-creazione-account'
INSTAGRAM_ACCOUNT_UPDATE_MODE = 'aggiorna-account-instagram'
TWO_FACTOR_REQUIRED_ON_ACCOUNT_UPDATE = 'codice-2fa-richiesto-per-aggiornamento-account'

UNKNOWN_ERROR = 'Inserisci un codice di sicurezza valido e riprova'
INVALID_CREDENTIALS = 'Nome utente o password errati. Riprova.'



def authenticate(username, password):
    try:
        user = User.objects.get(username=username)
        if user.check_password(password):
            return user
        return None
    except User.DoesNotExist:
        return None