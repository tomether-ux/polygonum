# Generated manually for adding cerca_per_categoria field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scambi', '0017_annuncio_disattivato_at'),
    ]

    operations = [
        # Rendi il campo titolo non obbligatorio (blank=True)
        migrations.AlterField(
            model_name='annuncio',
            name='titolo',
            field=models.CharField(max_length=200, blank=True),
        ),
        # Aggiungi il campo cerca_per_categoria
        migrations.AddField(
            model_name='annuncio',
            name='cerca_per_categoria',
            field=models.BooleanField(
                default=False,
                help_text="Se attivato, cerca qualsiasi oggetto nella categoria selezionata (solo per annunci 'cerco')",
                verbose_name='Cerco qualsiasi cosa in questa categoria'
            ),
        ),
    ]
