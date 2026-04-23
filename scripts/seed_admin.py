"""
Run once after first migrate to create a System Admin user.
Usage: python manage.py shell < scripts/seed_admin.py
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.users.models import User, UserRole

email = 'admin@judiciary.gm'
if not User.objects.filter(email=email).exists():
    user = User.objects.create_superuser(
        email=email,
        password='Admin1234!',
        first_name='System',
        last_name='Administrator',
        role=UserRole.SYSTEM_ADMIN,
    )
    print(f'✓ System admin created: {email} / Admin1234!')
else:
    print(f'System admin already exists: {email}')
