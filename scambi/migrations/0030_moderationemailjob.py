from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ('scambi', '0029_unique_user_email_ci'),
    ]

    operations = [
        migrations.CreateModel(
            name='ModerationEmailJob',
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
                ('image_reference', models.CharField(max_length=500)),
                ('image_url', models.URLField(max_length=2000)),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('pending', 'In attesa'),
                            ('processing', 'In elaborazione'),
                            ('sent', 'Inviata'),
                            ('failed', 'Fallita'),
                            ('cancelled', 'Annullata'),
                        ],
                        db_index=True,
                        default='pending',
                        max_length=20,
                    ),
                ),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                (
                    'next_attempt_at',
                    models.DateTimeField(
                        db_index=True,
                        default=django.utils.timezone.now,
                    ),
                ),
                ('locked_at', models.DateTimeField(blank=True, null=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('last_error_type', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'annuncio',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='moderation_email_job',
                        to='scambi.annuncio',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Email di moderazione in coda',
                'verbose_name_plural': 'Email di moderazione in coda',
                'ordering': ['next_attempt_at', 'created_at'],
                'indexes': [
                    models.Index(
                        fields=['status', 'next_attempt_at'],
                        name='moderation_queue_due_idx',
                    ),
                ],
            },
        ),
    ]
