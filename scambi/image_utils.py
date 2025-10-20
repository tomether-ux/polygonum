"""
Utility per gestire e ottimizzare le immagini caricate dagli utenti
"""
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


def optimize_image(image_field, max_width=1200, max_height=1200, quality=85):
    """
    Ridimensiona e ottimizza un'immagine caricata

    Args:
        image_field: ImageField di Django
        max_width: Larghezza massima in pixel
        max_height: Altezza massima in pixel
        quality: Qualità JPEG (1-100, default 85)

    Returns:
        InMemoryUploadedFile: Immagine ottimizzata pronta per il salvataggio
    """
    # Apri l'immagine
    img = Image.open(image_field)

    # Converti in RGB se necessario (per PNG con trasparenza)
    if img.mode in ('RGBA', 'LA', 'P'):
        # Crea sfondo bianco per immagini trasparenti
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Ottieni dimensioni originali
    width, height = img.size

    # Calcola nuove dimensioni mantenendo le proporzioni
    if width > max_width or height > max_height:
        # Calcola il ratio per ridimensionare
        ratio = min(max_width / width, max_height / height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)

        # Ridimensiona con qualità alta (LANCZOS)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Salva in BytesIO con compressione
    output = BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True)
    output.seek(0)

    # Crea nuovo file Django
    return InMemoryUploadedFile(
        output,
        'ImageField',
        f"{image_field.name.split('.')[0]}.jpg",
        'image/jpeg',
        sys.getsizeof(output),
        None
    )


def get_image_dimensions(image_field):
    """
    Ottiene dimensioni di un'immagine senza caricarla completamente

    Args:
        image_field: ImageField di Django

    Returns:
        tuple: (width, height) in pixel
    """
    try:
        img = Image.open(image_field)
        return img.size
    except Exception:
        return (0, 0)


def is_image_too_large(image_field, max_size_mb=5):
    """
    Verifica se un'immagine supera una certa dimensione

    Args:
        image_field: ImageField di Django
        max_size_mb: Dimensione massima in MB

    Returns:
        bool: True se l'immagine è troppo grande
    """
    return image_field.size > (max_size_mb * 1024 * 1024)
