from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scambi', '0030_moderationemailjob'),
    ]

    operations = [
        migrations.AddField(
            model_name='calcolometadata',
            name='ricalcolo_richiesto_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Ultima modifica agli annunci ancora da considerare',
                null=True,
            ),
        ),
    ]
