# Generated manually for adding condizione field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scambi', '0023_cleanup_old_location_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='annuncio',
            name='condizione',
            field=models.CharField(
                choices=[
                    ('nuovo', 'Come nuovo'),
                    ('ottimo', 'Ottime condizioni'),
                    ('buono', 'Buone condizioni'),
                    ('usato', 'Usato'),
                    ('danneggiato', 'Danneggiato/Da riparare')
                ],
                default='usato',
                help_text="Indica lo stato attuale dell'oggetto",
                max_length=15,
                verbose_name="Condizioni dell'oggetto"
            ),
        ),
    ]
