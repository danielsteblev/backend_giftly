from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0002_alter_user_email_alter_user_first_name_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            # Удаляем существующий внешний ключ
            "ALTER TABLE authtoken_token DROP CONSTRAINT IF EXISTS authtoken_token_user_id_35299eff_fk_auth_user_id;",
            # Создаем новый внешний ключ, указывающий на нашу кастомную модель
            "ALTER TABLE authtoken_token ADD CONSTRAINT authtoken_token_user_id_fk FOREIGN KEY (user_id) REFERENCES api_user(id) ON DELETE CASCADE;"
        ),
    ] 