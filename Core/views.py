from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from .models import User, PasswordResetCode
from bot.bot import InstagramBot
from .utils import *
from django.urls import reverse
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone

def Home(request):

    return render(request, 'index.html')

def Register(request):

    context = {
        'username': '',
        'email': ''
    }

    if request.method == 'POST':

        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('pswd')

        data_has_error = False

        if not (username and email and password):
            messages.error(request, 'Tutti i campi sono obbligatori')
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Il nome utente esiste già')
            data_has_error = True

        if User.objects.filter(email=email).exists():
            messages.error(request, "L'email esiste già")
            data_has_error = True

        if len(password) < 5:
            messages.error(request, 'La password deve contenere almeno 5 caratteri')
            data_has_error = True

        if data_has_error:
            context = {
                'username': username,
                'email': email
            }

            return render(request, 'register.html', context)

        User.objects.create_user(username=username, email=email, password=password)

        messages.success(request, "Account creato con successo! Potrai accedere una volta che il tuo account sarà attivato")
        return redirect('login')
        
    return render(request, 'register.html', context)


def Login(request):

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('pswd')

        if not (username and password):
            messages.error(request, 'Il nome utente e la password devono essere forniti')
            return redirect('login')

        user = authenticate(username=username, password=password)
        if user is not None:

            if not user.is_active:
                messages.error(request, 'Il tuo account non è stato attivato')
                return redirect('login')

            login(request, user)
            return redirect('accounts')
        
        messages.error(request, 'Nome utente o password non validi')
        return redirect('login')
    
    return render(request, 'login.html')


def Logout(request):

    logout(request)
    return redirect('home')

def ForgotPassword(request):

    if request.method == 'POST':
        email = request.POST.get('email')

        if not User.objects.filter(email=email).exists():
            messages.error(request, "L'email fornita non è registrata a nessun utente")
            return redirect('forgot-password')
        
        user = User.objects.get(email=email)
        new_password_reset = PasswordResetCode(user=user)
        new_password_reset.save()
    
        password_reset_url = reverse('reset-password', kwargs={'reset_id': new_password_reset.reset_id})
        full_password_reset_url = f'{request.scheme}://{request.get_host()}{password_reset_url}'
        
        email_body = f'Reimposta la tua password usando il link qui sotto:\n\n\n{full_password_reset_url}'
        
        email_message = EmailMessage(
            'Reimposta la tua password',
            email_body,
            settings.EMAIL_HOST_USER,
            [email]
        )
        
        email_message.fail_silently = True
        email_message.send()

        return redirect(f"{reverse('forgot-password')}?password_reset_sent=True")

    return render(request, 'forgot-password.html')


def ResetPassword(request, reset_id):
    
    try:
        password_reset_id = PasswordResetCode.objects.get(reset_id=reset_id)

        if request.method == "POST":
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')

            passwords_have_error = False

            if password != confirm_password:
                passwords_have_error = True
                messages.error(request, 'Le password non coincidono')

            if len(password) < 5:
                passwords_have_error = True
                messages.error(request, 'La password deve contenere almeno 5 caratteri')

            expiration_time = password_reset_id.created_when + timezone.timedelta(minutes=10)

            if timezone.now() > expiration_time:
                passwords_have_error = True
                messages.error(request, 'Il link per il reset è scaduto.')

                password_reset_id.delete()

            if not passwords_have_error:
                user = password_reset_id.user
                user.set_password(password)
                user.save()

                password_reset_id.delete()

                messages.success(request, 'Password reimpostata. Procedi al login')
                return redirect('login')
            else:
                # reindirizza alla pagina di reset della password e mostra gli errori
                return redirect('reset-password', reset_id=reset_id)

    except PasswordResetCode.DoesNotExist:
        
        # reindirizza alla pagina "password dimenticata" se il codice non esiste
        messages.error(request, 'ID di reset non valido')
        return redirect('forgot-password')

    return render(request, 'reset-password.html')


@login_required
def Profile(request):

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password and confirm_password and password == confirm_password:
            user = request.user
            user.set_password(password)
            user.save()
            messages.success(request, 'Password aggiornata con successo')
        
        else:
            messages.error(request, 'Le password non coincidono')
        
        return redirect('profile')

    return render(request, 'profile.html')


@login_required
def Account(request, old_username=None):

    bot = InstagramBot(user=request.user.username)

    # L'utente sta tentando di aggiornare l'account
    if request.method == 'POST' and old_username is not None:

        username = request.POST.get('username')
        password = request.POST.get('password', None)
        number_of_followers = request.POST.get('number_of_followers')
       
        status, message = bot.update_ig_account(old_username, username, password, number_of_followers)

        if status:
            messages.success(request, message)
            return redirect('accounts')
        
        elif not status and message == VERIFICATION_CODE_REQUIRED_FOR_ACCOUNT:
            
            request.session['username'] = username
            request.session['password'] = password
            request.session['old_username'] = old_username
            request.session['number_of_followers'] = number_of_followers
            request.session['mode'] = INSTAGRAM_ACCOUNT_UPDATE_MODE

            return redirect('verification-code')
        
        elif not status and message == TWO_FACTOR_REQUIRED_FOR_ACCOUNT:
            
            request.session['username'] = username
            request.session['password'] = password
            request.session['old_username'] = old_username
            request.session['number_of_followers'] = number_of_followers
            request.session['mode'] = TWO_FACTOR_REQUIRED_ON_ACCOUNT_UPDATE

            return redirect('verification-code')
        
        else:
            messages.error(request, message)
            return redirect('update-instagram-acount', old_username=old_username)

    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')
        number_of_followers = request.POST.get('number_of_followers')

        if not (username and password and number_of_followers):
            messages.error(request, 'Tutti i campi sono obbligatori')
            return redirect('add-instagram-acount')
        
        if (int(number_of_followers) + request.user.current_allocation) > request.user.max_close_friends_allocation:
            messages.error(request, f"Il numero di follower inserito supera il tuo attuale piano. Lo spazio di allocazione rimasto è {request.user.max_close_friends_allocation - request.user.current_allocation} follower. Contatta l'amministratore per ottenere più spazio di allocazione.")
            return redirect('add-instagram-acount')
        
        creation_status, message = bot.create_new_account(username, password, int(number_of_followers))

        if creation_status:
            messages.success(request, message)
            return redirect('accounts')
        
        elif not creation_status and message == VERIFICATION_CODE_REQUIRED_FOR_ACCOUNT:
            
            request.session['username'] = username
            request.session['password'] = password
            request.session['number_of_followers'] = number_of_followers
            request.session['mode'] = 'create-account'
            return redirect('verification-code')
        
        elif not creation_status and message == TWO_FACTOR_REQUIRED_FOR_ACCOUNT:
            
            request.session['username'] = username
            request.session['password'] = password
            request.session['number_of_followers'] = number_of_followers
            request.session['mode'] = INSTAGRAM_ACCOUNT_CREATION_MODE
            return redirect('verification-code')

        else:
            messages.error(request, message)
            return redirect('add-instagram-acount')

    context = {
        'account': False
    }

    if old_username:
        username, password, config = bot._get_account(old_username)
        context = {
            'account': True,
            'username': username,
            'config': config
        }
        
    return render(request, 'add-account.html', context)


@login_required
def VerificationCode(request):

    bot = InstagramBot(user=request.user.username)

    if request.method == 'POST':
        
        code = request.POST.get('code')

        if not code:
            messages.error(request, 'Il codice di verifica è obbligatorio')
            return redirect('verification-code')
        
        if len(code) != 6:
            messages.error(request, 'Il codice di verifica deve essere lungo 6 caratteri')
            return redirect('verification-code')

        username = request.session['username'] 
        password = request.session['password'] 
        old_username = request.session.get('old_username', None)
        number_of_followers = request.session['number_of_followers']
        mode = request.session['mode']

        # Aggiornamento dell'account
        if mode == INSTAGRAM_ACCOUNT_UPDATE_MODE:
            creation_status, message = bot.update_ig_account(
                old_username=old_username,
                username=username, 
                password=password, 
                number_of_followers=number_of_followers, 
                verification_code=code
            )

        elif mode == TWO_FACTOR_REQUIRED_ON_ACCOUNT_UPDATE:
            creation_status, message = bot.update_ig_account(
                old_username=old_username,
                username=username, 
                password=password, 
                number_of_followers=number_of_followers, 
                two_factor_verification_code=code
            )

        # Creazione dell'account
        elif mode == TWO_FACTOR_REQUIRED_FOR_ACCOUNT:
            creation_status, message = bot.create_new_account(
                username, 
                password, 
                int(number_of_followers),
                two_factor_verification_code=code
            )
        
        else:  # mode = create-account
            creation_status, message = bot.create_new_account(
                username, 
                password, 
                int(number_of_followers), 
                verification_code=code
            )

        if creation_status:
            messages.success(request, message)
            return redirect('accounts')
        
        else:
            messages.error(request, message)
            return redirect('verification-code')

    return render(request, 'code.html')


@login_required
def UserConnectedAccounts(request):

    bot = InstagramBot(user=request.user.username)
    accounts = bot.get_user_accounts()

    context = {'accounts': accounts}
    return render(request, 'accounts.html', context)

@login_required
def DeleteIGAccount(request, username):

    bot = InstagramBot(user=request.user.username)
    status, deletion_message = bot.delete_ig_account(username)

    if status:
        messages.success(request, deletion_message)
    else:
        messages.error(request, deletion_message)

    return redirect('accounts')

@login_required
def GetFollowers(request, username):

    if username:
        bot = InstagramBot(user=request.user.username)
        status, message = bot.initialise_scrape_followers_task(username)
        
        messages.success(request, message) if status else messages.error(request, message)
        return redirect('accounts')
    
    return redirect('accounts')

@login_required
def ResetAccountFollowers(request, username):

    if username:
        bot = InstagramBot(user=request.user.username)
        status, message = bot.reset_user_followers(username)        

        messages.success(request, message) if status else messages.error(request, message)

    return redirect('accounts')

@login_required
def AddFollowersToCloseFriends(request, username):

    if username:
        bot = InstagramBot(user=request.user.username)
        status, message = bot.intialize_close_friends_add(username)        

        messages.success(request, message) if status else messages.error(request, message)

    return redirect('accounts')

@login_required
def AccountDetail(request, username):

    return render(request, 'account.html', {'username': username})

@login_required
def Faq(request):

    return render(request, 'faq.html')