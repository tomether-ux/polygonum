# Generated manually for cleanup of old location system
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scambi', '0022_add_provincia_model'),
    ]

    operations = [
        # Rendi provincia_obj e citta obbligatori (NOT NULL)
        migrations.AlterField(
            model_name='userprofile',
            name='provincia_obj',
            field=models.ForeignKey(
                help_text='Seleziona la tua provincia',
                on_delete=models.deletion.PROTECT,
                to='scambi.provincia',
                verbose_name='Provincia'
            ),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='citta',
            field=models.CharField(
                help_text='Nome della tua città o comune',
                max_length=100,
                verbose_name='Città/Comune'
            ),
        ),

        # Rimuovi i vecchi campi da UserProfile
        migrations.RemoveField(
            model_name='userprofile',
            name='citta_obj',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='citta_old',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='provincia',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='regione',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='latitudine',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='longitudine',
        ),

        # Elimina i modelli obsoleti
        migrations.DeleteModel(
            name='DistanzaCitta',
        ),
        migrations.DeleteModel(
            name='Citta',
        ),
    ]
