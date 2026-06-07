from django.db import migrations

def clear_mock_avatars(apps, schema_editor):
    Profile = apps.get_model('users', 'Profile')
    for profile in Profile.objects.all():
        # Clean up mock avatar URLs so they fallback to initials
        if 'lokesh.png' in profile.avatar_url or 'unsplash.com' in profile.avatar_url:
            profile.avatar_url = ""
            profile.save()

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(clear_mock_avatars),
    ]
