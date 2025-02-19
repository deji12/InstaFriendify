from django.contrib import admin
from .models import *

class UserAdmin(admin.ModelAdmin):

    list_display = ['username', 'email', 'first_name', 'last_name', 'max_close_friends_allocation', 'current_allocation', 'is_active']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    list_filter = ['is_active']

admin.site.register(User, UserAdmin)
