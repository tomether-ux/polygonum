# Generated manually to clean old broken image paths from database

from django.db import migrations


def clean_old_images(apps, schema_editor):
    """Rimuove tutti i vecchi path di immagini rotte dal database"""
    Annuncio = apps.get_model('scambi', 'Annuncio')

    # Trova tutti gli annunci con immagini
    annunci_con_immagini = Annuncio.objects.exclude(immagine='').exclude(immagine=None)
    count = annunci_con_immagini.count()

    if count > 0:
        print(f"\n🧹 Pulizia immagini vecchie: trovati {count} annunci con immagini")

        # Cancella tutte le immagini (erano path locali rotti)
        for annuncio in annunci_con_immagini:
            annuncio.immagine = None
            annuncio.save()

        print(f"✅ {count} immagini vecchie cancellate. Ora usa Cloudinary!")
    else:
        print("✓ Nessuna vecchia immagine da cancellare")


def reverse_clean(apps, schema_editor):
    """Nessuna reverse operation - non possiamo ripristinare immagini rotte"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('scambi', '0019_alter_annuncio_immagine'),
    ]

    operations = [
        migrations.RunPython(clean_old_images, reverse_clean),
    ]
