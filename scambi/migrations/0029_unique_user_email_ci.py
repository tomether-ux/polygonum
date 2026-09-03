from django.db import migrations, models
from django.db.models import Count
from django.db.models.functions import Lower


CONSTRAINT_NAME = 'auth_user_email_ci_unique'


def add_case_insensitive_email_constraint(apps, schema_editor):
    """Aggiunge il vincolo solo dopo un controllo esplicito e non distruttivo."""
    User = apps.get_model('auth', 'User')

    duplicates_exist = (
        User.objects.exclude(email='')
        .annotate(normalized_email=Lower('email'))
        .values('normalized_email')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
        .exists()
    )
    if duplicates_exist:
        raise RuntimeError(
            'Migrazione interrotta: esistono ancora email duplicate senza '
            'distinzione tra maiuscole e minuscole. Esegui prima '
            '`python manage.py audit_account_integrity --details`. '
            'Nessun account è stato modificato.'
        )

    connection = schema_editor.connection
    if not (
        connection.features.supports_expression_indexes
        and connection.features.supports_partial_indexes
    ):
        raise RuntimeError(
            'Il database configurato non supporta il vincolo univoco '
            'case-insensitive richiesto per le email.'
        )

    constraint = models.UniqueConstraint(
        Lower('email'),
        condition=~models.Q(email=''),
        name=CONSTRAINT_NAME,
    )
    schema_editor.add_constraint(User, constraint)


def remove_case_insensitive_email_constraint(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    constraint = models.UniqueConstraint(
        Lower('email'),
        condition=~models.Q(email=''),
        name=CONSTRAINT_NAME,
    )
    schema_editor.remove_constraint(User, constraint)


class Migration(migrations.Migration):
    dependencies = [
        ('scambi', '0028_alter_propostacatena_stato_confermacompletamento_and_more'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(
            add_case_insensitive_email_constraint,
            remove_case_insensitive_email_constraint,
        ),
    ]
