# Generated manually based on model changes
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('scambi', '0021_add_moderation_fields'),
    ]

    operations = [
        # Crea il modello Provincia
        migrations.CreateModel(
            name='Provincia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sigla', models.CharField(help_text='Es: MI, RM, TO', max_length=2, unique=True, verbose_name='Sigla')),
                ('nome', models.CharField(help_text='Es: Milano, Roma, Torino', max_length=100, verbose_name='Nome')),
                ('regione', models.CharField(max_length=50, verbose_name='Regione')),
                ('latitudine', models.FloatField(verbose_name='Latitudine')),
                ('longitudine', models.FloatField(verbose_name='Longitudine')),
            ],
            options={
                'verbose_name': 'Provincia',
                'verbose_name_plural': 'Province',
                'ordering': ['nome'],
            },
        ),
        # Aggiungi campo provincia_obj a UserProfile
        migrations.AddField(
            model_name='userprofile',
            name='provincia_obj',
            field=models.ForeignKey(
                blank=True,
                help_text='Seleziona la tua provincia',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='scambi.provincia',
                verbose_name='Provincia'
            ),
        ),
        # Aggiungi campo citta (CharField) a UserProfile
        migrations.AddField(
            model_name='userprofile',
            name='citta',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Nome della tua città o comune (campo libero)',
                max_length=100,
                verbose_name='Città/Comune'
            ),
        ),
        # Rendi nullable i vecchi campi per retrocompatibilità
        migrations.AlterField(
            model_name='userprofile',
            name='provincia',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Provincia (vecchio)'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='regione',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Regione (vecchio)'),
        ),
    ]
