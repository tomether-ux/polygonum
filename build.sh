#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run migrations (include la migrazione 0020 che pulisce le immagini vecchie)
python manage.py migrate

# Carica le province italiane (solo se non esistono già)
python manage.py loaddata province_fixture.json --ignorenonexistent || echo "Province già caricate o errore durante il caricamento"

# Assegna provincia di default agli utenti senza provincia
python manage.py assign_default_provincia || echo "Errore nell'assegnazione provincia di default"