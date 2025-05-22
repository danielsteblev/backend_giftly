from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            # Удаляем существующий внешний ключ
            "ALTER TABLE django_admin_log DROP CONSTRAINT IF EXISTS django_admin_log_user_id_c564eba6_fk_auth_user_id;",
            # Создаем новый внешний ключ, указывающий на нашу кастомную модель
            "ALTER TABLE django_admin_log ADD CONSTRAINT django_admin_log_user_id_fk FOREIGN KEY (user_id) REFERENCES api_user(id) ON DELETE SET NULL;"
        ),
    ] 