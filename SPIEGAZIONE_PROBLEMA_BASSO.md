# 🔍 SPIEGAZIONE COMPLETA: Perché 'basso' bloccava le catene 'synth'

## 📋 Cosa è successo

Quando l'annuncio 'basso' era attivo:
- ✅ La pagina `/catene-scambio/` non mostrava NESSUNA catena per admin
- ✅ Disattivando 'basso', le catene con 'synth' sono ricomparse

## 🏗️ Architettura del sistema

Il sistema ha **2 componenti separati**:

### 1. **CycleCalculator** (GitHub repo separato)
- Esegue algoritmo DFS per trovare TUTTI i cicli possibili
- Salva i cicli nel database PostgreSQL nella tabella `CicloScambio`
- Viene eseguito periodicamente (es. ogni notte)

### 2. **Django App** (questo repo)
- Legge i cicli pre-calcolati dal DB
- Applica filtri (qualità, utente, etc.)
- Mostra i cicli all'utente nella view `/catene-scambio/`

## 🔄 Il flusso completo

```
[CycleCalculator GitHub]
   ↓ calcola cicli
   ↓ salva in DB
[CicloScambio table]
   ↓ legge dal DB
[get_cicli_precalcolati()]
   ↓ applica filtro qualità
[catene_scambio view]
   ↓ mostra all'utente
[Pagina /catene-scambio/]
```

## ❌ Il problema

**Il CycleCalculator ha salvato nel DB SOLO cicli con 'basso'**

Quando 'basso' era attivo, il CycleCalculator:
1. Ha trovato cicli che includono 'basso' + altri annunci
2. Questi cicli hanno SOLO match categoria (generico)
3. Li ha salvati nel database con `valido=True`
4. **NON ha salvato** le catene con 'synth' perché:
   - Gli utenti erano già "consumati" nei cicli con 'basso'
   - Oppure l'algoritmo DFS ha trovato prima i cicli con 'basso'
   - Oppure li ha dedupli cati perché coinvolgevano gli stessi utenti

Poi la Django App:
1. Legge i cicli dal DB con `get_cicli_precalcolati()`
2. Applica il filtro qualità con `calcola_qualita_ciclo()`
3. **Blocca TUTTI i cicli** perché hanno solo match categoria
4. Risultato: **0 catene visualizzate**

## ✅ Perché disattivando 'basso' ha funzionato

Quando hai disattivato 'basso':
1. I cicli con 'basso' restano nel DB
2. Ma `converti_ciclo_db_a_view_format()` alla linea **1556** li filtra:
   ```python
   if not annuncio.attivo:
       return None  # Ciclo scartato
   ```
3. Quindi i cicli con 'basso' vengono ignorati
4. **MA**: Le catene con 'synth' ancora NON ci sono nel DB!

**Come mai le vedi?** Due possibilità:
- Il CycleCalculator è stato rieseguito automaticamente stanotte
- Oppure nel DB c'erano GIÀ cicli con 'synth' che erano stati mascherati da quelli con 'basso'

## 🔧 SOLUZIONE PERMANENTE

Il problema è nel **CycleCalculator** (GitHub repo), non nella Django App.

### Opzione 1: Modificare l'algoritmo CycleCalculator

Il CycleCalculator dovrebbe:
1. **Trovare TUTTI i cicli possibili** (non solo i primi che trova)
2. **Salvare TUTTI i cicli** nel DB (non deduplicate per utente)
3. **Dare priorità ai match titolo** rispetto ai match categoria
4. Lasciare che il filtro qualità nella Django App faccia il lavoro

**File da modificare**: `cycle_calculator` repo (DFS algorithm)

### Opzione 2: Filtrare prima del salvataggio

Modificare il CycleCalculator per:
1. Calcolare la qualità PRIMA di salvare nel DB
2. Salvare SOLO cicli con match titolo (≥20 punti)
3. Non salvare cicli con solo match categoria

**Vantaggio**: Database più pulito, meno cicli inutili
**Svantaggio**: Più complesso, richiede sincronizzazione codice qualità

### Opzione 3: Workaround temporaneo

**Soluzione attuale (workaround)**:
1. Disattivare annunci con solo match categoria (come 'basso')
2. Ricalcolare i cicli
3. Le catene con match titolo appariranno

**Limitazione**: Non puoi avere annunci con solo match categoria

## 📊 Verifica

Per verificare quale scenario si è verificato, esegui:

```bash
python diagnosi_basso_produzione.py
```

Questo script ti dirà:
- Se 'basso' è attivo/disattivo
- Quanti cicli ci sono nel DB
- Quanti sono con match titolo vs categoria
- Se le catene 'synth' sono nel DB o no

## 🎯 Raccomandazione

**Per ora**: Lascia 'basso' disattivato finché non modifichi il CycleCalculator

**A lungo termine**: Modifica il CycleCalculator (Opzione 1) per:
- Trovare TUTTI i cicli
- Dare priorità ai match titolo
- Salvare cicli diversi anche se coinvolgono gli stessi utenti

Questo richiede modifiche al repo **cycle_calculator** su GitHub.

## 🔍 Debug

Se vuoi vedere esattamente cosa è nel DB:

```python
from scambi.models import CicloScambio
from scambi.matching import calcola_qualita_ciclo, get_cicli_precalcolati

# Carica cicli
risultato = get_cicli_precalcolati()
catene = risultato['catene']

# Analizza qualità
for catena in catene:
    punteggio, ha_match = calcola_qualita_ciclo(catena, return_tipo_match=True)
    print(f"Ciclo {catena['id_ciclo']}: {punteggio} punti, match titoli: {ha_match}")

    # Mostra annunci coinvolti
    for u in catena['utenti']:
        print(f"  {u['user'].username}: offre '{u['offerta'].titolo}' cerca '{u['richiede'].titolo}'")
```

---

**In sintesi**: Il problema NON è nel codice Django (che funziona correttamente), ma nel CycleCalculator che non trova/salva le catene con 'synth' quando 'basso' è presente.
