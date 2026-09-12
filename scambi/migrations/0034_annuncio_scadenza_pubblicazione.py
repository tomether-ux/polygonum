import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scambi', '0033_annuncio_modifiche_effettuate'),
    ]

    operations = [
        migrations.AddField(
            model_name='annuncio',
            name='pubblicato_at',
            field=models.DateTimeField(
                db_index=True,
                default=django.utils.timezone.now,
                help_text='Data da cui decorrono i 60 giorni di pubblicazione',
                verbose_name='Data ultima pubblicazione',
            ),
        ),
        migrations.AddField(
            model_name='annuncio',
            name='scaduto_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Data scadenza',
            ),
        ),
        migrations.AlterModelOptions(
            name='annuncio',
            options={
                'ordering': ['-pubblicato_at'],
                'verbose_name_plural': 'Annunci',
            },
        ),
    ]
