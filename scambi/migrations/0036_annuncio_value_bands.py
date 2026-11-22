from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('scambi', '0035_propostacatena_selezione_annunci')]
    operations = [
        migrations.AlterField(
            model_name='annuncio', name='fascia_prezzo',
            field=models.CharField(blank=True, null=True, max_length=20,
                verbose_name='Fascia di prezzo', help_text="Fascia di valore scelta dall'utente",
                choices=[('v1', 'Minima'), ('v2', 'Bassa'), ('v3', 'Medio-bassa'),
                         ('v4', 'Media'), ('v5', 'Medio-alta'), ('v6', 'Alta'), ('v7', 'Molto alta'),
                         ('economico', 'Economico'), ('basso', 'Basso'), ('medio', 'Medio'),
                         ('alto', 'Alto'), ('premium', 'Premium')]),
        ),
        migrations.AddField(
            model_name='annuncio', name='fascia_secondaria',
            field=models.CharField(blank=True, default='', max_length=20,
                choices=[('v1', 'Minima'), ('v2', 'Bassa'), ('v3', 'Medio-bassa'),
                         ('v4', 'Media'), ('v5', 'Medio-alta'), ('v6', 'Alta'), ('v7', 'Molto alta')]),
        ),
    ]
