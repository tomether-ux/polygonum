# Generated manually for adding disattivato_at field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scambi', '0016_userprofile_is_premium_userprofile_premium_scadenza'),
    ]

    operations = [
        migrations.AddField(
            model_name='annuncio',
            name='disattivato_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Timestamp di quando l\'annuncio è stato disattivato (per calcolo catene)',
                null=True,
                verbose_name='Data disattivazione'
            ),
        ),
    ]
