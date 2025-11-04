# 🔧 Piano per Modificare il CycleCalculator

## 🎯 Obiettivo

Fare in modo che il CycleCalculator salvi NEL DATABASE sia:
- Cicli con match titolo (specifico/parziale/sinonimo) ✅ ALTA PRIORITÀ
- Cicli con match categoria (generico) ⚠️ BASSA PRIORITÀ

In modo che la Django App possa poi filtrarli correttamente.

## 📋 Modifiche da fare

### 1. **Importare la funzione di qualità nel CycleCalculator**

Il CycleCalculator deve usare la STESSA logica di qualità della Django App.

**Opzioni**:
- **A)** Copiare `oggetti_compatibili_con_tipo()` nel CycleCalculator
- **B)** Importare `oggetti_compatibili_con_tipo()` dalla Django App (se possibile)
- **C)** Creare una libreria condivisa tra CycleCalculator e Django App

**Raccomandazione**: Opzione A (più semplice, evita dipendenze)

### 2. **Modificare l'algoritmo DFS**

Attualmente, l'algoritmo DFS probabilmente:
```python
def find_cycles(start_user, max_depth):
    for each possible_path:
        if is_valid_cycle(path):
            return path  # ❌ SI FERMA AL PRIMO!
```

Deve diventare:
```python
def find_cycles(start_user, max_depth):
    all_cycles = []
    for each possible_path:
        if is_valid_cycle(path):
            all_cycles.append(path)  # ✅ CONTINUA A CERCARE!
    return all_cycles
```

### 3. **Dare priorità ai match titolo**

Quando esplora i path, l'algoritmo deve preferire:
1. Match specifico (titolo esatto)
2. Match parziale (parole in comune)
3. Match sinonimo
4. Match categoria

**Implementazione**:
```python
def get_compatible_announcements(announcement, all_announcements):
    """
    Restituisce annunci compatibili ORDINATI per qualità match
    """
    compatible = []

    for ann in all_announcements:
        is_compatible, match_type = check_compatibility(announcement, ann)

        if is_compatible:
            # Assegna priorità
            priority = {
                'specifico': 1,
                'parziale': 2,
                'sinonimo': 3,
                'categoria': 4,
                'generico': 5
            }.get(match_type, 99)

            compatible.append((ann, match_type, priority))

    # Ordina per priorità (più bassa = migliore)
    compatible.sort(key=lambda x: x[2])

    return compatible
```

### 4. **Gestire cicli multipli per lo stesso gruppo di utenti**

Attualmente, il CycleCalculator probabilmente deduplica per utenti:
```python
seen_user_sets = set()

for cycle in all_cycles:
    user_set = frozenset(cycle.users)

    if user_set in seen_user_sets:
        continue  # ❌ SALTA DUPLICATI

    seen_user_sets.add(user_set)
    save_to_db(cycle)
```

Deve diventare:
```python
seen_cycles = {}  # user_set -> list of cycles

for cycle in all_cycles:
    user_set = frozenset(cycle.users)

    # Calcola qualità
    quality_score = calculate_quality(cycle)

    # Salva TUTTE le varianti (con match diversi)
    if user_set not in seen_cycles:
        seen_cycles[user_set] = []

    # Controlla se esiste già un ciclo identico
    is_duplicate = False
    for existing in seen_cycles[user_set]:
        if cycles_are_identical(cycle, existing):
            # Tieni quello con qualità migliore
            if quality_score > existing.quality:
                seen_cycles[user_set].remove(existing)
                seen_cycles[user_set].append(cycle)
            is_duplicate = True
            break

    if not is_duplicate:
        seen_cycles[user_set].append(cycle)

# Salva tutti i cicli
for user_set, cycles in seen_cycles.items():
    for cycle in cycles:
        save_to_db(cycle)
```

### 5. **Salvare il tipo di match nel DB**

Aggiungere metadati al ciclo per facilitare il debug:

```python
cycle_details = {
    'scambi': [...],
    'punteggio_qualita': quality_score,
    'match_types': {  # NUOVO!
        'specifico': count_specific_matches,
        'parziale': count_partial_matches,
        'sinonimo': count_synonym_matches,
        'categoria': count_category_matches,
        'generico': count_generic_matches
    },
    'ha_match_titoli': has_title_matches  # NUOVO!
}
```

## 🔍 File da modificare (presumibilmente)

Nel repo CycleCalculator:

1. **`cycle_finder.py`** (o simile) - Algoritmo DFS
   - Modificare per trovare TUTTI i cicli
   - Aggiungere ordinamento per priorità match

2. **`compatibility.py`** (o simile) - Logica compatibilità
   - Copiare `oggetti_compatibili_con_tipo()` dalla Django App
   - Assicurare che restituisca `(compatible, match_type)`

3. **`deduplication.py`** (o simile) - Gestione duplicati
   - Permettere cicli multipli per stesso gruppo utenti
   - Solo se hanno match diversi

4. **`quality.py`** (nuovo?) - Calcolo qualità
   - Copiare `calcola_qualita_ciclo()` dalla Django App
   - O almeno la logica per determinare `ha_match_titoli`

## ✅ Test da fare dopo le modifiche

1. **Test con 'basso' attivo**:
   - Admin ha: cerco synth, cerco basso
   - hhh ha: offro synth, offro basso
   - Dovrebbe trovare DUE cicli:
     - Ciclo 1: admin ↔ hhh (synth) - ALTA QUALITÀ
     - Ciclo 2: admin ↔ hhh (basso) - BASSA QUALITÀ

2. **Test catena lunga**:
   - A offre X (match titolo), cerca Y
   - B offre Y (match titolo), cerca Z
   - C offre Z (match categoria), cerca X
   - Dovrebbe trovare la catena anche se C ha match categoria

3. **Test performance**:
   - Con 100+ annunci, verificare che non sia troppo lento
   - Potrebbe essere necessario un limite (es. max 5 cicli per gruppo utenti)

## 📊 Metriche di successo

Dopo le modifiche, in produzione:
- ✅ Le catene con 'synth' appaiono anche se 'basso' è attivo
- ✅ Il DB contiene sia cicli alta che bassa qualità
- ✅ Il filtro nella Django App blocca correttamente quelli bassa qualità
- ✅ Gli utenti vedono solo catene con match titolo

## ⚠️ Attenzioni

1. **Performance**: Trovare TUTTI i cicli può essere costoso
   - Considera un timeout (es. 5 minuti max)
   - O un limite per utente (es. max 10 cicli per user)

2. **Database size**: Più cicli = DB più grande
   - Monitora la dimensione della tabella `CicloScambio`
   - Considera pulizia periodica cicli vecchi

3. **Sincronizzazione codice**: La logica compatibilità DEVE essere identica
   - Se modifichi `oggetti_compatibili_con_tipo()` in Django App
   - Devi aggiornare anche nel CycleCalculator

## 🚀 Deployment

1. Modificare il CycleCalculator
2. Testare in locale
3. Deploy su Render
4. **IMPORTANTE**: Invalidare tutti i cicli vecchi e ricalcolare:
   ```python
   CicloScambio.objects.all().update(valido=False)
   # Poi esegui il CycleCalculator
   ```
5. Verificare che le catene appaiano correttamente
6. Riattivare 'basso' e verificare che non blocchi più

---

**Prossimo step**: Dimmi dove si trova il repo CycleCalculator e possiamo iniziare le modifiche!
