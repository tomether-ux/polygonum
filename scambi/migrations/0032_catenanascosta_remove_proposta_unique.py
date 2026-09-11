import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scambi', '0031_calcolometadata_ricalcolo_richiesto_at'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='propostacatena',
            unique_together=set(),
        ),
        migrations.CreateModel(
            name='CatenaNascosta',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('data_nascosta', models.DateTimeField(auto_now_add=True)),
                (
                    'ciclo',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='nascosta_da',
                        to='scambi.cicloscambio',
                    ),
                ),
                (
                    'utente',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='catene_nascoste',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Catena nascosta',
                'verbose_name_plural': 'Catene nascoste',
                'ordering': ['-data_nascosta'],
                'constraints': [
                    models.UniqueConstraint(
                        fields=('utente', 'ciclo'),
                        name='unique_hidden_cycle_per_user',
                    ),
                ],
            },
        ),
    ]
