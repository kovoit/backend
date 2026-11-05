from django.db import migrations, models


class Migration(migrations.Migration):
    """Objet des codes e-mail (D-77) : les codes existants sont des codes de vérification."""

    dependencies = [
        ("accounts", "0007_telephones_format_togolais"),
    ]

    operations = [
        migrations.AddField(
            model_name="otpcode",
            name="objet",
            field=models.CharField(
                choices=[
                    ("verification_email", "Vérification de l'adresse e-mail"),
                    ("reinitialisation", "Réinitialisation du mot de passe"),
                ],
                default="verification_email",
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.AddIndex(
            model_name="otpcode",
            index=models.Index(
                fields=["email", "objet", "cree_le"], name="accounts_ot_email_731efe_idx"
            ),
        ),
    ]
