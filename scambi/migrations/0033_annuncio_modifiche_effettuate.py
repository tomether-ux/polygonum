from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scambi', '0032_catenanascosta_remove_proposta_unique'),
    ]

    operations = [
        migrations.AddField(
            model_name='annuncio',
            name='modifiche_effettuate',
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Numero di modifiche effettuate dall'utente dopo la pubblicazione",
                verbose_name='Modifiche effettuate',
            ),
        ),
    ]
