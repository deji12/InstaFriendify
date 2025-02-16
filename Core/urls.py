from django.urls import path
from . import views

urlpatterns = [
    path('', views.Home, name='home'),
    path('register/', views.Register, name='register'),
    path('login/', views.Login, name='login'),
    path('profile/', views.Profile, name='profile'),
    path('logout/', views.Logout, name='logout'),
    path('add-instagram-acount/', views.Account, name='add-instagram-acount'),
    path('edit-instagram-acount/<str:old_username>/', views.Account, name='update-instagram-acount'),
    path('accounts/', views.UserConnectedAccounts, name='accounts'),
    path('delete-connected-account/<str:username>/', views.DeleteIGAccount, name='delete-ig-account'),
    path('get-account-followers/<str:username>/', views.GetFollowers, name='get-account-followers'),
    path('reset-account-followers/<str:username>/', views.ResetAccountFollowers, name='reset-account-followers'),
    path('add-followers-to-close-friends/<str:username>/', views.AddFollowersToCloseFriends, name='add-followers-to-close-friends'),
    path('account/<str:username>/', views.AccountDetail, name='account-detail'),
    path('help/', views.Faq, name='help'),
]