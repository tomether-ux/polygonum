from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scambi', '0034_annuncio_scadenza_pubblicazione'),
    ]

    operations = [
        migrations.AddField(
            model_name='propostacatena',
            name='selezione_annunci',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    'Una coppia offerta/richiesta per ogni passaggio della catena'
                ),
            ),
        ),
    ]
