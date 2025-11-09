#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate

# One-time cleanup: Delete old broken images
echo "🧹 Cleaning old broken images..."
python manage.py cancella_immagini_vecchie || echo "⚠️  No images to clean or cleanup skipped"