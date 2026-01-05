# Implementazione Fasce di Prezzo per Matching Equo

## Cosa è stato fatto

Sono state create **5 fasce di prezzo fisse** per categorizzare gli annunci e facilitare match più equi:

| Fascia | Range | Badge Color |
|--------|-------|-------------|
| Economico | €0 - 20 | Grigio |
| Basso | €20 - 50 | Blu chiaro |
| Medio | €50 - 150 | Blu |
| Alto | €150 - 500 | Arancione |
| Premium | €500+ | Rosso |

## Modifiche al codice

### 1. Model Annuncio (`scambi/models.py`)
- ✅ Aggiunto campo `fascia_prezzo` (CharField con choices)
- ✅ Metodo `calcola_fascia_prezzo()` per calcolo automatico
- ✅ Metodo `get_fascia_display_badge()` per mostrare badge HTML
- ✅ Il campo viene popolato automaticamente al `save()` in base a `prezzo_stimato`

### 2. Migrazione database
- ✅ File: `scambi/migrations/0025_aggiungi_fascia_prezzo.py`
- Aggiunge il campo `fascia_prezzo` alla tabella `annuncio`

### 3. Comando per popolare annunci esistenti
- ✅ File: `scambi/management/commands/popola_fasce_prezzo.py`
- Calcola e assegna la fascia a tutti gli annunci esistenti con prezzo

## Come applicare le modifiche

### Passo 1: Applicare la migrazione

```bash
python manage.py migrate scambi
```

Questo creerà la colonna `fascia_prezzo` nel database.

### Passo 2: Popolare le fasce per gli annunci esistenti

Prima, verifica cosa verrebbe fatto (dry-run):

```bash
python manage.py popola_fasce_prezzo --dry-run
```

Vedrai un output tipo:
```
📊 Trovati 150 annunci con prezzo da classificare

✅ Simulati 150 annunci

📈 Distribuzione per fascia:
   economico :   12 (  8.0%) ████
   basso     :   35 ( 23.3%) ███████████
   medio     :   78 ( 52.0%) ██████████████████████████
   alto      :   20 ( 13.3%) ██████
   premium   :    5 (  3.3%) █
```

Se il risultato è OK, esegui senza dry-run:

```bash
python manage.py popola_fasce_prezzo
```

### Passo 3: Verifica

Controlla nel Django admin o shell:

```python
python manage.py shell

>>> from scambi.models import Annuncio
>>> Annuncio.objects.filter(fascia_prezzo='medio').count()
78
>>> annuncio = Annuncio.objects.filter(prezzo_stimato__isnull=False).first()
>>> print(f"Prezzo: €{annuncio.prezzo_stimato} - Fascia: {annuncio.get_fascia_prezzo_display()}")
Prezzo: €100.00 - Fascia: Medio (€50-150)
```

## Comportamento automatico

Da ora in poi:

1. **Creazione nuovo annuncio**: L'utente seleziona una fascia di prezzo (es. "Medio (€50-150)") tramite badge colorati. Il sistema calcola automaticamente `prezzo_stimato = 100` (centro della fascia).

2. **Modifica annuncio**: L'utente vede la fascia attualmente selezionata e può cambiarla cliccando su un altro badge. Il `prezzo_stimato` viene ricalcolato automaticamente.

3. **Annunci senza prezzo**: L'utente può non selezionare alcuna fascia (opzione "Nessuna fascia"). In questo caso `fascia_prezzo = None` e `prezzo_stimato = None`.

### Mappatura fascia → prezzo

Il sistema calcola il prezzo dal centro della fascia:

- **Economico (€0-20)** → prezzo_stimato = €10
- **Basso (€20-50)** → prezzo_stimato = €35
- **Medio (€50-150)** → prezzo_stimato = €100
- **Alto (€150-500)** → prezzo_stimato = €325
- **Premium (€500+)** → prezzo_stimato = €750

## Interfaccia utente

### ✅ Selettore fasce in creazione/modifica annuncio

Il campo prezzo numerico è stato sostituito con un selettore visuale che mostra **badge metallici cliccabili**:

- **Economico (€0-20)**: Grigio acciaio
- **Basso (€20-50)**: Bronzo
- **Medio (€50-150)**: Argento
- **Alto (€150-500)**: Oro
- **Premium (€500+)**: Platino con effetto luminoso

L'utente clicca sul badge desiderato e il sistema calcola automaticamente il `prezzo_stimato`.

### ✅ Badge nelle liste e dettagli

**Lista annunci** (`lista_annunci.html`):
- Quadratino colorato 12x12px accanto al prezzo
- Tooltip al passaggio del mouse con la fascia completa

**Dettaglio annuncio** (`dettaglio_annuncio.html`):
- Badge completo con icona + nome + range di prezzo
- Posizionato sotto il prezzo nell'angolo superiore destro

**Profilo utente** (`profilo_utente.html`):
- Quadratino colorato nelle card degli annunci

### 2. Implementare filtro nelle catene di scambio

In `catene_scambio.html`, aggiungi un filtro:

```html
<div class="mb-3">
    <label>Filtra per fascia di prezzo</label>
    <select name="fascia" class="form-select">
        <option value="">Tutte le fasce</option>
        <option value="economico">Economico (€0-20)</option>
        <option value="basso">Basso (€20-50)</option>
        <option value="medio">Medio (€50-150)</option>
        <option value="alto">Alto (€150-500)</option>
        <option value="premium">Premium (€500+)</option>
    </select>
</div>
```

E nella view `catene_scambio()`:

```python
fascia_filtro = request.GET.get('fascia', '')

if fascia_filtro:
    # Filtra solo catene dove TUTTI gli oggetti sono della fascia selezionata
    cicli_filtrati = []
    for ciclo in cicli:
        annunci = estrai_annunci_da_ciclo(ciclo)
        fasce = [a.fascia_prezzo for a in annunci if a.fascia_prezzo]

        # Tutti devono essere della stessa fascia richiesta
        if all(f == fascia_filtro for f in fasce):
            cicli_filtrati.append(ciclo)

    cicli = cicli_filtrati
```

## Note tecniche

- Il campo è `blank=True, null=True` quindi è opzionale
- Gli annunci senza prezzo avranno `fascia_prezzo = None`
- Il calcolo avviene sempre al save(), quindi è sempre aggiornato
- Le fasce sono definite in `Annuncio.FASCIA_PREZZO_CHOICES`

## Rollback (se necessario)

Per rimuovere tutto:

```bash
python manage.py migrate scambi 0024_annuncio_condizione
```

Poi rimuovi il campo dal model e la migrazione.
