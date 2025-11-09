# Generated manually to switch from ImageField to CloudinaryField

from django.db import migrations
import cloudinary.models


class Migration(migrations.Migration):

    dependencies = [
        ('scambi', '0018_add_cerca_per_categoria_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='annuncio',
            name='immagine',
            field=cloudinary.models.CloudinaryField(blank=True, folder='annunci', max_length=255, null=True, verbose_name='image'),
        ),
    ]
