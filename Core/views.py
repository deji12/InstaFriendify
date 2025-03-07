from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from .models import User
from bot.bot import InstagramBot
from .utils import authenticate

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
            messages.error(request, 'All fields are required')
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            data_has_error = True

        if len(password) < 5:
            messages.error(request, 'Password must be at least 5 characters long')
            data_has_error = True

        if data_has_error:
            context = {
                'username': username,
                'email': email
            }

            return render(request, 'register.html', context)

        User.objects.create_user(username=username, email=email, password=password)

        messages.success(request, "Account created successfully! You will be able to login once your account is activated")
        return redirect('login')
    return render(request, 'register.html', context)

def Login(request):

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('pswd')

        if not (username and password):
            messages.error(request, 'Username and password must be provided')
            return redirect('login')

        user = authenticate(username=username, password=password)
        if user is not None:
 
            if not user.is_active:
                messages.error(request, 'Your account has not been activated')
                return redirect('login')

            login(request, user)
            return redirect('accounts')
        
        messages.error(request, 'Invalid username or password')
        return redirect('login')
    
    return render(request, 'login.html')

def Logout(request):

    logout(request)
    return redirect('home')


@login_required
def Profile(request):

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password and confirm_password and password == confirm_password:
            user = request.user
            user.set_password(password)
            user.save()
            messages.success(request, 'Password updated successfully')
        
        else:
            messages.error(request, 'Passwords do not match')
        
        return redirect('profile')

    return render(request, 'profile.html')


@login_required
def Account(request, old_username=None):

    bot = InstagramBot(user=request.user.username)

    if request.method == 'POST' and old_username is not None:

        username = request.POST.get('username')
        password = request.POST.get('password')
        # number_of_followers = request.POST.get('number_of_followers')

        # status, message = bot.update_ig_account(old_username, username, password, int(number_of_followers))
        status, message = bot.update_ig_account(old_username, username, password)

        if status:
            messages.success(request, message)
            return redirect('accounts')
        elif not status and message == 'Enter the verification code sent to your email or phone number':
            request.session['username'] = username
            request.session['password'] = password
            request.session['mode'] = 'update'
            return redirect('verification-code')
        else:
            messages.error(request, message)
            return redirect('update-instagram-acount', old_username=old_username)

        # messages.success(request, message) if status else messages.error(request, message)
        # return redirect('update-instagram-acount', old_username=old_username)

    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')
        number_of_followers = request.POST.get('number_of_followers')

        if not (username and password and number_of_followers):
            messages.error(request, 'All fields are required')
            return redirect('add-instagram-acount')
        
        if (int(number_of_followers) + request.user.current_allocation) > request.user.max_close_friends_allocation:
            messages.error(request, f"The number of followers entered exceeds your current plan. You allocation space left is {request.user.max_close_friends_allocation - request.user.current_allocation} followers. Contact the admin to get more allocation space.")
            return redirect('add-instagram-acount')
        
        creation_status, message = bot.create_new_account(username, password, int(number_of_followers))

        if creation_status:
            messages.success(request, message)
            return redirect('accounts')
        elif not creation_status and message == 'Enter the verification code sent to your email or phone number':
            request.session['username'] = username
            request.session['password'] = password
            request.session['number_of_followers'] = number_of_followers
            request.session['mode'] = 'create'
            return redirect('verification-code')
        else:
            messages.error(request, message)
            return redirect('add-instagram-acount')

    context = {}

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
            messages.error(request, 'Verification code is required')
            return redirect('verification-code')
        
        if len(code) != 6:
            messages.error(request, 'Verification code must be 6 characters long')
            return redirect('verification-code')

        username = request.session['username'] 
        password = request.session['password'] 
        number_of_followers = request.session['number_of_followers']
        mode = request.session['mode']

        if mode == 'update':
            creation_status, message = bot.update_ig_account(username, password, verification_code=code)
        else:
            creation_status, message = bot.create_new_account(username, password, int(number_of_followers), verification_code=code)

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