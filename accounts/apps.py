from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.contrib.auth import get_user_model
import os

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        def create_admin_user(sender, **kwargs):
            User = get_user_model()
            username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
            email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@gmail.com')
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'Admin@Daymart')

            if not User.objects.filter(username=username).exists():
                print(f"Creating superuser: {username}")
                User.objects.create_superuser(username=username, email=email, password=password)

        post_migrate.connect(create_admin_user, sender=self)
