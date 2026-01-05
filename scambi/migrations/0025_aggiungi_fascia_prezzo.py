# Generated manually for adding fascia_prezzo field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scambi', '0024_annuncio_condizione'),
    ]

    operations = [
        migrations.AddField(
            model_name='annuncio',
            name='fascia_prezzo',
            field=models.CharField(
                blank=True,
                choices=[
                    ('economico', 'Economico (€0-20)'),
                    ('basso', 'Basso (€20-50)'),
                    ('medio', 'Medio (€50-150)'),
                    ('alto', 'Alto (€150-500)'),
                    ('premium', 'Premium (€500+)')
                ],
                help_text='Calcolata automaticamente dal prezzo stimato per facilitare match equi',
                max_length=20,
                null=True,
                verbose_name='Fascia di prezzo'
            ),
        ),
    ]
