from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.mail import EmailMessage
from .models import User
from django.conf import settings

@receiver(pre_save, sender=User)
def on_user_activation(sender, instance, **kwargs):
    """
    Send an email to the user when their account is activated (is_active is set to True).
    """
    if instance.is_active:
        try:
            # Check if the user was previously inactive
            previous_user = User.objects.get(pk=instance.pk)
            if not previous_user.is_active:
                # Construct the email message
                subject = "Your Account Has Been Activated"
                message = f"""Hello {instance.username},\n\nYour account has been activated and you have been allocated a space for {instance.max_close_friends_allocation} followers.\nYou can now log in and start using our services.\n\nThank you!"""
                from_email = settings.EMAIL_HOST_USER  # Replace with your email
                recipient_list = [instance.email]

                # Create and send the email
                email_message = EmailMessage(
                    subject=subject,
                    body=message,
                    from_email=from_email,
                    to=recipient_list,
                )
                email_message.fail_silently = True
                email_message.send()
        except User.DoesNotExist:
            # This is a new user, so no need to send an activation email
            pass