from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import UserCreationForm  # Se usi il form base
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .matching import trova_catene_scambio, trova_scambi_diretti, filtra_catene_per_utente, trova_catene_per_annuncio, trova_scambi_diretti_ottimizzato, trova_catene_scambio_ottimizzato, filtra_catene_per_utente_ottimizzato, trova_catene_per_annuncio_ottimizzato
from .models import Annuncio, PropostaCatena, RispostaProposta, CicloScambio
import importlib
import hashlib
import hmac
import os
from . import matching
from .debug_views import debug_basso, debug_view_catene  # Debug temporaneo

def test_matching(request):
    """Vista per testare l'algoritmo di matching con debug dettagliato"""
    import importlib
    from . import matching

    # Forza il reload del modulo
    importlib.reload(matching)
    from .matching import oggetti_compatibili_con_tipo, trova_catene_scambio

    html = "<h1>🧪 Test Matching Algorithm</h1>"
    html += "<style>body { font-family: monospace; } .match { color: green; } .no-match { color: red; }</style>"

    # Test 1: Verifica match specifici
    html += "<h2>🔍 Test 1: Match Specifici</h2>"

    # Trova annunci synth
    synth_offerto = Annuncio.objects.filter(tipo='offro', titolo__icontains='synth', attivo=True).first()
    synth_cercato = Annuncio.objects.filter(tipo='cerco', titolo__icontains='synth', attivo=True).first()

    # Trova annunci bici
    bici_offerto = Annuncio.objects.filter(tipo='offro', titolo__icontains='bici', attivo=True).first()
    bici_cercato = Annuncio.objects.filter(tipo='cerco', titolo__icontains='bici', attivo=True).first()

    test_pairs = []
    if synth_offerto and synth_cercato:
        test_pairs.append((synth_offerto, synth_cercato, "SYNTH → SYNTH"))
    if bici_offerto and bici_cercato:
        test_pairs.append((bici_offerto, bici_cercato, "BICI → BICI"))

    for offerto, cercato, nome in test_pairs:
        html += f"<h3>{nome}</h3>"
        html += f"<p><strong>Offerto:</strong> '{offerto.titolo}' by {offerto.utente.username}</p>"
        html += f"<p><strong>Cercato:</strong> '{cercato.titolo}' by {cercato.utente.username}</p>"

        compatible, tipo_match = oggetti_compatibili_con_tipo(offerto, cercato)
        if compatible:
            html += f"<p class='match'>✅ MATCH TROVATO! Tipo: {tipo_match}</p>"
        else:
            html += f"<p class='no-match'>❌ NESSUN MATCH</p>"
        html += "<hr>"

    # Test 2: Catene complete
    html += "<h2>🔗 Test 2: Catene Complete</h2>"
    catene = trova_catene_scambio_ottimizzato()

    if catene:
        html += f"<p class='match'>🎉 Trovate {len(catene)} catene!</p>"
        for i, catena in enumerate(catene[:3], 1):  # Mostra solo le prime 3
            html += f"<h4>Catena {i}</h4>"
            html += f"<p>Utenti: {', '.join(catena['utenti'])}</p>"
            html += f"<p>Qualità: {catena.get('categoria_qualita', 'N/A')}</p>"
    else:
        html += "<p class='no-match'>❌ Nessuna catena trovata</p>"

    # Test 3: Conteggio annunci
    html += "<h2>📊 Test 3: Database Status</h2>"
    offro_count = Annuncio.objects.filter(tipo='offro', attivo=True).count()
    cerco_count = Annuncio.objects.filter(tipo='cerco', attivo=True).count()
    html += f"<p>Annunci 'offro' attivi: {offro_count}</p>"
    html += f"<p>Annunci 'cerco' attivi: {cerco_count}</p>"

    return HttpResponse(html)

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .matching import trova_catene_scambio
from .models import Annuncio, Categoria
from .forms import AnnuncioForm

def home(request):
    """Vista principale del sito"""
    annunci_recenti = Annuncio.objects.filter(attivo=True).order_by('-data_creazione')[:6]
    categorie = Categoria.objects.all()
    
    return render(request, 'scambi/home.html', {
        'annunci_recenti': annunci_recenti,
        'categorie': categorie
    })

def lista_annunci(request):
    """Mostra tutti gli annunci"""
    tipo_filtro = request.GET.get('tipo')
    categoria_filtro = request.GET.get('categoria')
    
    annunci = Annuncio.objects.filter(attivo=True)
    
    if tipo_filtro:
        annunci = annunci.filter(tipo=tipo_filtro)
    if categoria_filtro:
        annunci = annunci.filter(categoria_id=categoria_filtro)
    
    categorie = Categoria.objects.all()
    
    return render(request, 'scambi/lista_annunci.html', {
        'annunci': annunci,
        'categorie': categorie,
        'tipo_filtro': tipo_filtro,
        'categoria_filtro': categoria_filtro
    })

def dettaglio_annuncio(request, annuncio_id):
    """Mostra i dettagli di un singolo annuncio"""
    annuncio = get_object_or_404(Annuncio, id=annuncio_id, attivo=True)

    return render(request, 'scambi/dettaglio_annuncio.html', {
        'annuncio': annuncio
    })

@login_required
def crea_annuncio(request):
    """Crea un nuovo annuncio"""
    # Ottieni o crea il profilo dell'utente
    profilo, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = AnnuncioForm(request.POST, request.FILES)  # Aggiungi request.FILES
        if form.is_valid():
            annuncio = form.save(commit=False)
            annuncio.utente = request.user

            # Controlla i limiti prima di salvare
            tipo = annuncio.tipo
            puo_creare, messaggio_errore = profilo.puo_creare_annuncio(tipo)

            if not puo_creare:
                messages.error(request, messaggio_errore)
                return render(request, 'scambi/crea_annuncio.html', {
                    'form': form,
                    'profilo': profilo
                })

            annuncio.save()
            messages.success(request, 'Annuncio creato con successo!')
            return redirect('lista_annunci')
    else:
        form = AnnuncioForm()

    # Calcola statistiche per il template
    context = {
        'form': form,
        'profilo': profilo,
        'count_offro': profilo.get_count_annunci('offro'),
        'count_cerco': profilo.get_count_annunci('cerco'),
        'limite_offro': profilo.get_limite_annunci('offro'),
        'limite_cerco': profilo.get_limite_annunci('cerco'),
        'rimanenti_offro': profilo.get_annunci_rimanenti('offro'),
        'rimanenti_cerco': profilo.get_annunci_rimanenti('cerco'),
    }

    return render(request, 'scambi/crea_annuncio.html', context)

@login_required
def modifica_annuncio(request, annuncio_id):
    """Modifica un annuncio esistente"""
    annuncio = get_object_or_404(Annuncio, id=annuncio_id, utente=request.user)

    if request.method == 'POST':
        form = AnnuncioForm(request.POST, instance=annuncio)
        if form.is_valid():
            form.save()
            messages.success(request, 'Annuncio modificato con successo!')
            return redirect('profilo_utente', username=request.user.username)
    else:
        form = AnnuncioForm(instance=annuncio)

    return render(request, 'scambi/modifica_annuncio.html', {
        'form': form,
        'annuncio': annuncio
    })

@login_required
def elimina_annuncio(request, annuncio_id):
    """Elimina un annuncio"""
    annuncio = get_object_or_404(Annuncio, id=annuncio_id, utente=request.user)

    if request.method == 'POST':
        annuncio.delete()
        messages.success(request, 'Annuncio eliminato con successo!')
        return redirect('profilo_utente', username=request.user.username)

    return render(request, 'scambi/conferma_eliminazione.html', {'annuncio': annuncio})

@login_required
def attiva_annuncio(request, annuncio_id):
    """Attiva un annuncio disattivato"""
    annuncio = get_object_or_404(Annuncio, id=annuncio_id, utente=request.user)

    # Controlla i limiti prima di attivare
    profilo, created = UserProfile.objects.get_or_create(user=request.user)

    # IMPORTANTE: Quando riattivi, devi contare come se l'annuncio fosse già attivo
    # perché puo_creare_annuncio conta solo annunci attivi, ma questo è ancora inattivo
    if not profilo.is_premium:
        limite = profilo.get_limite_annunci(annuncio.tipo)
        count_attivi = profilo.get_count_annunci(annuncio.tipo)

        # Conta anche l'annuncio che stiamo per riattivare
        if count_attivi >= limite:
            tipo_display = "offro" if annuncio.tipo == "offro" else "cerco"
            messages.error(
                request,
                f'Non puoi riattivare questo annuncio: hai raggiunto il limite di {limite} annunci "{tipo_display}". '
                f'Passa a Premium per annunci illimitati!'
            )
            return redirect('profilo_utente', username=request.user.username)

    annuncio.attivo = True
    annuncio.save()
    messages.success(request, f'Annuncio "{annuncio.titolo}" attivato con successo!')
    return redirect('profilo_utente', username=request.user.username)

@login_required
def disattiva_annuncio(request, annuncio_id):
    """Disattiva un annuncio"""
    annuncio = get_object_or_404(Annuncio, id=annuncio_id, utente=request.user)
    annuncio.attivo = False
    annuncio.save()
    messages.success(request, f'Annuncio "{annuncio.titolo}" disattivato con successo!')
    return redirect('profilo_utente', username=request.user.username)

def catene_scambio(request):
    """Mostra le catene di scambio divise per qualità"""
    # Controlla se è stata richiesta una nuova ricerca
    cerca_nuove = request.GET.get('cerca') == 'true'
    # Filtro per annuncio specifico
    annuncio_filtro_id = request.GET.get('annuncio_id')

    if cerca_nuove:
        import time

        print("🔍 RICERCA CATENE ATTIVATA MANUALMENTE")

        try:
            start_time = time.time()
            timeout_seconds = 15  # 15 secondi di timeout (ultra-sicuro)

            # Se l'utente è autenticato, mostra solo le catene che lo coinvolgono
            if request.user.is_authenticated:
                # Controlla se l'utente ha annunci attivi
                annunci_utente = Annuncio.objects.filter(utente=request.user, attivo=True)
                if annunci_utente.exists():
                    print(f"🔍 Filtrando catene per utente: {request.user.username}")

                    # OTTIMIZZAZIONE: Se è stato selezionato un annuncio specifico, usa ricerca ottimizzata
                    if annuncio_filtro_id:
                        try:
                            annuncio_specifico = Annuncio.objects.get(id=annuncio_filtro_id, utente=request.user, attivo=True)
                            print(f"🎯 RICERCA OTTIMIZZATA per annuncio: {annuncio_specifico.titolo}")

                            # Usa la funzione ottimizzata che cerca solo catene per questo annuncio (solo specifiche)
                            tutte_catene = trova_catene_per_annuncio_ottimizzato(annuncio_specifico, max_lunghezza=6, includi_generiche=False)

                            elapsed = time.time() - start_time
                            messages.success(request, f'🎯 Ricerca ottimizzata completata in {elapsed:.1f} secondi. Trovate {len(tutte_catene)} catene per "{annuncio_specifico.titolo}"!')

                        except Annuncio.DoesNotExist:
                            print("❌ Annuncio specificato non valido, eseguo ricerca completa")
                            # Fallback alla ricerca completa se l'annuncio non esiste
                            annuncio_filtro_id = None

                    # Se non c'è filtro specifico, esegui ricerca completa
                    if not annuncio_filtro_id:
                        # Esegui ricerca con limitazioni per evitare timeout
                        print("⚡ Caricamento scambi diretti da database...")
                        scambi_diretti = trova_scambi_diretti_ottimizzato()

                        if time.time() - start_time > timeout_seconds:
                            messages.error(request, 'Ricerca interrotta per timeout. Troppi dati da elaborare.')
                            # IMPORTANTE: Filtra scambi diretti anche in caso di timeout
                            from .matching import calcola_qualita_ciclo, filtra_catene_per_utente_ottimizzato
                            scambi_diretti_specifici = []
                            for c in scambi_diretti:
                                _, ha_match_titoli = calcola_qualita_ciclo(c, return_tipo_match=True)
                                if ha_match_titoli:
                                    scambi_diretti_specifici.append(c)
                            scambi_diretti_utente, _ = filtra_catene_per_utente_ottimizzato(
                                scambi_diretti_specifici, [], request.user
                            )
                            tutte_catene = scambi_diretti_utente
                        else:
                            print("⏰ Inizio ricerca catene lunghe...")
                            try:
                                # Import della funzione aggiornata
                                from .matching import calcola_qualita_ciclo

                                # Carica tutte le catene dal database ottimizzato (2-6 utenti)
                                catene = trova_catene_scambio_ottimizzato()

                                if time.time() - start_time > timeout_seconds:
                                    messages.warning(request, 'Ricerca parziale completata (timeout raggiunto). Mostrando solo scambi diretti.')
                                    # IMPORTANTE: Filtra scambi diretti anche in caso di timeout parziale
                                    scambi_diretti_specifici = []
                                    for c in scambi_diretti:
                                        _, ha_match_titoli = calcola_qualita_ciclo(c, return_tipo_match=True)
                                        if ha_match_titoli:
                                            scambi_diretti_specifici.append(c)
                                    scambi_diretti_utente, _ = filtra_catene_per_utente_ottimizzato(
                                        scambi_diretti_specifici, [], request.user
                                    )
                                    tutte_catene = scambi_diretti_utente
                                else:
                                    # Filtra SOLO catene con match sui titoli (specifico/parziale)
                                    # Prima filtriamo gli scambi diretti
                                    scambi_diretti_specifici = []
                                    for c in scambi_diretti:
                                        punteggio, ha_match_titoli = calcola_qualita_ciclo(c, return_tipo_match=True)
                                        c['punteggio_qualita'] = punteggio
                                        if ha_match_titoli:
                                            scambi_diretti_specifici.append(c)

                                    # Poi filtriamo le catene lunghe
                                    catene_specifiche = []
                                    for c in catene:
                                        # Calcola qualità e determina se ha match sui titoli
                                        punteggio, ha_match_titoli = calcola_qualita_ciclo(c, return_tipo_match=True)
                                        c['punteggio_qualita'] = punteggio

                                        # Includi SOLO se ha match sui titoli
                                        if ha_match_titoli:
                                            catene_specifiche.append(c)

                                    # Filtra tutto per l'utente attuale (solo catene specifiche)
                                    scambi_diretti_utente, catene_lunghe_utente = filtra_catene_per_utente_ottimizzato(
                                        scambi_diretti_specifici, catene_specifiche, request.user
                                    )

                                    # Ricomponi le catene filtrate
                                    tutte_catene = scambi_diretti_utente + catene_lunghe_utente

                                    elapsed = time.time() - start_time
                                    messages.success(request, f'Ricerca completata in {elapsed:.1f} secondi. Trovate {len(tutte_catene)} catene con parole in comune nei titoli!')
                            except Exception as e:
                                print(f"❌ Errore durante ricerca catene lunghe: {type(e).__name__}: {e}")
                                import traceback
                                traceback.print_exc()
                                # IMPORTANTE: Filtra scambi diretti anche in caso di errore
                                from .matching import calcola_qualita_ciclo, filtra_catene_per_utente_ottimizzato
                                scambi_diretti_specifici = []
                                for c in scambi_diretti:
                                    _, ha_match_titoli = calcola_qualita_ciclo(c, return_tipo_match=True)
                                    if ha_match_titoli:
                                        scambi_diretti_specifici.append(c)
                                scambi_diretti_utente, _ = filtra_catene_per_utente_ottimizzato(
                                    scambi_diretti_specifici, [], request.user
                                )
                                tutte_catene = scambi_diretti_utente
                                messages.warning(request, f'Errore nella ricerca catene lunghe: {type(e).__name__}. Mostrando solo scambi diretti.')
                else:
                    tutte_catene = []
                    messages.warning(request, 'Non hai annunci attivi! Pubblica un annuncio per partecipare agli scambi.')
            else:
                # Utente non autenticato - ricerca molto limitata
                print("🔍 Ricerca per utente non autenticato (limitata a scambi diretti)")
                try:
                    scambi_diretti = trova_scambi_diretti_ottimizzato()
                    tutte_catene = scambi_diretti
                    elapsed = time.time() - start_time
                    messages.info(request, f'Ricerca completata in {elapsed:.1f} secondi. Solo scambi diretti per utenti non registrati.')
                except Exception as e:
                    print(f"Errore durante ricerca: {e}")
                    tutte_catene = []
                    messages.error(request, 'Errore durante la ricerca. Riprova più tardi.')

        except Exception as e:
            print(f"Errore generale durante ricerca catene: {e}")
            messages.error(request, 'Errore durante la ricerca delle catene. Riprova più tardi.')
            tutte_catene = []
    else:
        # Se non è stata richiesta ricerca, carica catene dal DB
        print("📋 Caricamento catene dal database (senza ricalcolo)")

        if request.user.is_authenticated:
            # Controlla se l'utente ha annunci attivi
            annunci_utente = Annuncio.objects.filter(utente=request.user, attivo=True)
            if annunci_utente.exists():
                try:
                    # Carica cicli pre-calcolati dal DB
                    from .matching import (
                        get_cicli_precalcolati,
                        filtra_catene_per_utente_ottimizzato,
                        calcola_qualita_ciclo
                    )

                    risultato = get_cicli_precalcolati()
                    scambi_diretti = risultato['scambi_diretti']
                    catene = risultato['catene']

                    # Filtra TUTTI i cicli (scambi diretti + catene) per match titoli
                    scambi_diretti_specifici = []
                    for c in scambi_diretti:
                        _, ha_match_titoli = calcola_qualita_ciclo(c, return_tipo_match=True)
                        if ha_match_titoli:
                            scambi_diretti_specifici.append(c)

                    catene_specifiche_temp = []
                    for c in catene:
                        _, ha_match_titoli = calcola_qualita_ciclo(c, return_tipo_match=True)
                        if ha_match_titoli:
                            catene_specifiche_temp.append(c)

                    # Filtra per utente
                    scambi_diretti_utente, catene_lunghe_utente = filtra_catene_per_utente_ottimizzato(
                        scambi_diretti_specifici, catene_specifiche_temp, request.user
                    )

                    tutte_catene = scambi_diretti_utente + catene_lunghe_utente

                    print(f"✅ Caricate {len(tutte_catene)} catene dal DB per {request.user.username}")

                except Exception as e:
                    print(f"❌ Errore caricamento catene dal DB: {e}")
                    tutte_catene = []
            else:
                tutte_catene = []
        else:
            tutte_catene = []

    # Rimuovi duplicati
    catene_uniche = []
    combinazioni_viste = set()

    for catena in tutte_catene:
        # Ordina per ID utente invece di oggetti utente completi
        utenti_ids = tuple(sorted([u['user'].id for u in catena['utenti']]))
        if utenti_ids not in combinazioni_viste:
            combinazioni_viste.add(utenti_ids)
            catene_uniche.append(catena)

    # Le catene sono già state filtrate per qualità e utente
    # Non serve ri-filtrare
    catene_specifiche = catene_uniche


    # Filtra per annuncio specifico se richiesto
    if annuncio_filtro_id and request.user.is_authenticated:
        try:
            annuncio_filtro = Annuncio.objects.get(id=annuncio_filtro_id, utente=request.user, attivo=True)

            # Filtra solo catene che coinvolgono questo annuncio
            catene_specifiche = [c for c in catene_specifiche if any(
                item.get('annuncio', {}).id == int(annuncio_filtro_id) if hasattr(item.get('annuncio', {}), 'id')
                else False for item in c.get('annunci_coinvolti', [])
            )]
        except Annuncio.DoesNotExist:
            pass  # Ignora se l'annuncio non esiste

    # Ordina per lunghezza e punteggio
    catene_specifiche.sort(key=lambda x: (len(x.get('utenti', [])), -x.get('punteggio_qualita', 0)))

    # Aggiungi flag per i preferiti e hash se l'utente è autenticato
    if request.user.is_authenticated:
        for catena in catene_specifiche:
            # Riordina la catena in modo che l'utente loggato sia sempre il primo
            riordina_catena_per_utente(catena, request.user)

            catena['is_favorita'] = is_catena_preferita(request.user, catena)
            catena['hash_catena'] = genera_hash_catena(catena)
            # Converti la catena in JSON string per il template
            catena['json_data'] = json.dumps(catena, default=str)

    # Aggiungi annunci utente per dropdown filtro
    miei_annunci = []
    annuncio_selezionato = None
    if request.user.is_authenticated:
        miei_annunci = Annuncio.objects.filter(utente=request.user, attivo=True).order_by('-data_creazione')
        if annuncio_filtro_id:
            try:
                annuncio_selezionato = Annuncio.objects.get(id=annuncio_filtro_id, utente=request.user, attivo=True)
            except Annuncio.DoesNotExist:
                pass

    # UNIFICATO: Raggruppa TUTTE le catene (2-6) per numero di partecipanti
    catene_2 = [c for c in catene_specifiche if len(c.get('utenti', [])) == 2]
    catene_3 = [c for c in catene_specifiche if len(c.get('utenti', [])) == 3]
    catene_4 = [c for c in catene_specifiche if len(c.get('utenti', [])) == 4]
    catene_5 = [c for c in catene_specifiche if len(c.get('utenti', [])) == 5]
    catene_6 = [c for c in catene_specifiche if len(c.get('utenti', [])) == 6]

    return render(request, 'scambi/catene_scambio.html', {
        'catene_specifiche': catene_specifiche,
        'catene_2': catene_2,
        'catene_3': catene_3,
        'catene_4': catene_4,
        'catene_5': catene_5,
        'catene_6': catene_6,
        'totale_catene': len(catene_specifiche),
        'totale_scambi_diretti': len(catene_2),
        'totale_catene_lunghe': len(catene_specifiche) - len(catene_2),
        'ricerca_eseguita': cerca_nuove,
        'user_filtered': request.user.is_authenticated and cerca_nuove,
        'miei_annunci': miei_annunci,
        'annuncio_selezionato': annuncio_selezionato
    })

# La funzione test_matching rimane uguale...
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from .forms import CustomUserCreationForm, UserProfileForm
from .email_utils import send_verification_email
from .models import UserProfile
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required

def register(request):
    import logging
    logger = logging.getLogger(__name__)

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)

        # Debug: Log form data received
        logger.info(f"Registration attempt - Form data: {request.POST}")
        logger.info(f"City from form: {request.POST.get('citta')}")
        logger.info(f"Province from form: {request.POST.get('provincia')}")

        if form.is_valid():
            # Debug: Log cleaned data
            logger.info(f"Form valid - Cleaned data: {form.cleaned_data}")
            logger.info(f"City from cleaned_data: {form.cleaned_data.get('citta')}")
            logger.info(f"Province from cleaned_data: {form.cleaned_data.get('provincia')}")

            try:
                user = form.save()
                logger.info(f"User created successfully: {user.username}")

                # Invia email di verifica con timeout gestito
                try:
                    user_profile = UserProfile.objects.get(user=user)
                    logger.info(f"UserProfile found - City: {user_profile.citta}, Province: {user_profile.provincia}")

                    # Usa la nuova funzione con timeout esteso per SendGrid
                    from .email_utils import send_verification_email_with_timeout
                    email_result = send_verification_email_with_timeout(request, user, user_profile, timeout_seconds=30)

                    if email_result["success"]:
                        messages.success(request,
                            f'🎉 Registrazione completata! Ti abbiamo inviato un\'email di verifica a {user.email}. '
                            'Controlla la tua casella di posta e clicca sul link per attivare il tuo account.')
                    elif email_result["message"] == "timeout":
                        messages.warning(request,
                            f'✅ Registrazione completata! L\'invio dell\'email di verifica a {user.email} ha richiesto più di 30 secondi. '
                            'L\'email potrebbe essere ancora in elaborazione e arrivare nei prossimi minuti. '
                            'Se non la ricevi entro 10 minuti, contatta il supporto.')
                        logger.warning(f"Email timeout (30s) for user {user.username} but registration successful")
                    else:
                        messages.warning(request,
                            f'✅ Registrazione completata! Tuttavia c\'è stato un problema tecnico nell\'invio immediato dell\'email di verifica a {user.email}. '
                            'L\'email dovrebbe arrivare comunque nei prossimi minuti. Se non la ricevi, contatta il supporto.')
                        logger.error(f"Email sending failed for user {user.username}: {email_result.get('error', 'Unknown error')}")

                except UserProfile.DoesNotExist as e:
                    logger.error(f"UserProfile not found for user {user.username}: {e}")
                    messages.error(request, 'Errore nella creazione del profilo utente.')
                except Exception as e:
                    logger.error(f"Error during profile retrieval/email sending: {e}")
                    messages.warning(request,
                        f'✅ Registrazione completata! Tuttavia c\'è stato un problema nell\'invio dell\'email di verifica. '
                        'L\'email dovrebbe arrivare nei prossimi minuti.')

            except Exception as e:
                logger.error(f"Error during user creation: {e}")
                messages.error(request, f'Errore durante la registrazione: {e}')
                return render(request, 'registration/register.html', {'form': form})

            return redirect('login')
        else:
            # Debug: Log form errors
            logger.warning(f"Form validation failed - Errors: {form.errors}")
            # Aggiungi messaggi di errore per il debug
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/register.html', {'form': form})

def verify_email(request, token):
    """Vista per verificare l'email tramite token"""
    try:
        user_profile = UserProfile.objects.get(email_verification_token=token)

        if not user_profile.email_verified:
            # Attiva utente e profilo
            user_profile.email_verified = True
            user_profile.email_verification_token = None
            user_profile.save()

            user = user_profile.user
            user.is_active = True
            user.save()

            messages.success(request, 'Email verificata con successo! Ora puoi accedere al tuo account.')
        else:
            messages.info(request, 'Email già verificata precedentemente.')

    except UserProfile.DoesNotExist:
        messages.error(request, 'Token di verifica non valido o scaduto.')

    return redirect('login')

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def form_invalid(self, form):
        # Aggiungi messaggi di errore per il debug
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f'Login error - {field}: {error}')

        return super().form_invalid(form)

def profilo_utente(request, username):
    """Vista pubblica del profilo utente con i suoi annunci"""
    utente = get_object_or_404(User, username=username)

    try:
        profilo = UserProfile.objects.get(user=utente)
    except UserProfile.DoesNotExist:
        # Se l'utente non ha profilo, creane uno vuoto
        profilo = UserProfile.objects.create(user=utente, citta="Non specificata")

    # Se è il proprio profilo, mostra tutti gli annunci (anche disattivati)
    # Se è il profilo di un altro, mostra solo quelli attivi
    if request.user == utente:
        annunci = Annuncio.objects.filter(utente=utente).order_by('-data_creazione')
    else:
        annunci = Annuncio.objects.filter(utente=utente, attivo=True).order_by('-data_creazione')

    # Dividi annunci per tipo
    annunci_offro = annunci.filter(tipo='offro')
    annunci_cerco = annunci.filter(tipo='cerco')

    # Conta solo gli annunci attivi per le statistiche pubbliche
    annunci_attivi = Annuncio.objects.filter(utente=utente, attivo=True)

    context = {
        'utente': utente,
        'profilo': profilo,
        'annunci_offro': annunci_offro,
        'annunci_cerco': annunci_cerco,
        'totale_annunci': annunci_attivi.count(),
        'is_own_profile': request.user == utente
    }

    # Se è il proprio profilo e l'utente è loggato, aggiungi la sezione "I Miei Scambi"
    if request.user == utente and request.user.is_authenticated:
        # Controlla se l'utente ha annunci attivi
        ha_annunci = annunci_attivi.exists()
        ricerca_eseguita = request.GET.get('cerca_scambi', False)

        if ricerca_eseguita and ha_annunci:
            # Esegui ricerca completa
            scambi_diretti = trova_scambi_diretti_ottimizzato()
            catene = trova_catene_scambio_ottimizzato()

            # Separa catene per qualità (come nella vista originale)
            catene_alta_qualita = [c for c in catene if c.get('categoria_qualita') == 'alta']
            catene_generiche = [c for c in catene if c.get('categoria_qualita') == 'generica']

            # Filtra tutto per l'utente attuale
            scambi_diretti_utente, catene_lunghe_utente = filtra_catene_per_utente_ottimizzato(
                scambi_diretti, catene_alta_qualita + catene_generiche, request.user
            )

            # Ri-separa per qualità dopo il filtraggio
            catene_alta_qualita_utente = [c for c in catene_lunghe_utente if c.get('categoria_qualita') == 'alta']
            catene_generiche_utente = [c for c in catene_lunghe_utente if c.get('categoria_qualita') == 'generica']

            # Separa scambi diretti per qualità
            scambi_diretti_alta = [s for s in scambi_diretti_utente if s.get('categoria_qualita') == 'alta']
            scambi_diretti_generici = [s for s in scambi_diretti_utente if s.get('categoria_qualita') == 'generica']

            # Calcola totali
            totale_scambi_diretti = len(scambi_diretti_utente)
            totale_catene_lunghe = len(catene_lunghe_utente)
            totale_catene = totale_scambi_diretti + totale_catene_lunghe

            context.update({
                'scambi_ricerca_eseguita': True,
                'scambi_diretti_alta': scambi_diretti_alta,
                'scambi_diretti_generici': scambi_diretti_generici,
                'catene_alta_qualita': catene_alta_qualita_utente,
                'catene_generiche': catene_generiche_utente,
                'totale_scambi_diretti': totale_scambi_diretti,
                'totale_catene_lunghe': totale_catene_lunghe,
                'totale_catene': totale_catene,
            })

            messages.info(request, f'Trovate {totale_catene} opportunità di scambio per i tuoi annunci!')

        elif ricerca_eseguita and not ha_annunci:
            # Utente ha cercato ma non ha annunci
            context.update({
                'scambi_ricerca_eseguita': True,
                'scambi_diretti_alta': [],
                'scambi_diretti_generici': [],
                'catene_alta_qualita': [],
                'catene_generiche': [],
                'totale_scambi_diretti': 0,
                'totale_catene_lunghe': 0,
                'totale_catene': 0,
                'nessun_annuncio': True,
            })

            messages.warning(request,
                'Non hai annunci attivi! Pubblica un annuncio per trovare opportunità di scambio.')

        else:
            # Prima visita o utente senza annunci
            context.update({
                'scambi_ricerca_eseguita': False,
                'ha_annunci': ha_annunci,
            })

    return render(request, 'scambi/profilo_utente.html', context)

@login_required
def modifica_profilo(request):
    """Vista per modificare il proprio profilo"""
    try:
        profilo = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profilo = UserProfile.objects.create(user=request.user, citta="")

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profilo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profilo aggiornato con successo!')
            return redirect('profilo_utente', username=request.user.username)
    else:
        form = UserProfileForm(instance=profilo)

        # DEBUG: Verifica quante città ci sono nel queryset
        from scambi.models import Citta
        citta_count = Citta.objects.count()
        queryset_count = form.fields['citta_obj'].queryset.count()
        print(f"DEBUG modifica_profilo: Città nel DB={citta_count}, Queryset nel form={queryset_count}")

    # Carica tutte le città per il template
    from scambi.models import Citta
    citta_list = Citta.objects.all().order_by('nome')

    return render(request, 'scambi/modifica_profilo.html', {
        'form': form,
        'profilo': profilo,
        'citta_list': citta_list
    })

def custom_logout(request):
    """View personalizzata per il logout"""
    logout(request)
    return render(request, 'registration/logout.html')

@login_required
def mie_catene_scambio(request):
    """Vista personalizzata che mostra solo le catene di scambio rilevanti per l'utente loggato"""

    # Controlla se l'utente ha annunci attivi
    annunci_utente = Annuncio.objects.filter(utente=request.user, attivo=True)
    ha_annunci = annunci_utente.exists()

    ricerca_eseguita = request.GET.get('cerca', False)

    if ricerca_eseguita and ha_annunci:
        # Esegui ricerca completa
        scambi_diretti = trova_scambi_diretti_ottimizzato()
        catene = trova_catene_scambio_ottimizzato()

        # Separa catene per qualità (come nella vista originale)
        catene_alta_qualita = [c for c in catene if c.get('categoria_qualita') == 'alta']
        catene_generiche = [c for c in catene if c.get('categoria_qualita') == 'generica']

        # Filtra tutto per l'utente attuale
        scambi_diretti_utente, catene_lunghe_utente = filtra_catene_per_utente_ottimizzato(
            scambi_diretti, catene_alta_qualita + catene_generiche, request.user
        )

        # Ri-separa per qualità dopo il filtraggio
        catene_alta_qualita_utente = [c for c in catene_lunghe_utente if c.get('categoria_qualita') == 'alta']
        catene_generiche_utente = [c for c in catene_lunghe_utente if c.get('categoria_qualita') == 'generica']

        # Separa scambi diretti per qualità
        scambi_diretti_alta = [s for s in scambi_diretti_utente if s.get('categoria_qualita') == 'alta']
        scambi_diretti_generici = [s for s in scambi_diretti_utente if s.get('categoria_qualita') == 'generica']

        # Calcola totali
        totale_scambi_diretti = len(scambi_diretti_utente)
        totale_catene_lunghe = len(catene_lunghe_utente)
        totale_catene = totale_scambi_diretti + totale_catene_lunghe

        context = {
            'ricerca_eseguita': True,
            'scambi_diretti_alta': scambi_diretti_alta,
            'scambi_diretti_generici': scambi_diretti_generici,
            'catene_alta_qualita': catene_alta_qualita_utente,
            'catene_generiche': catene_generiche_utente,
            'totale_scambi_diretti': totale_scambi_diretti,
            'totale_catene_lunghe': totale_catene_lunghe,
            'totale_catene': totale_catene,
            'personalizzato': True,  # Flag per template
        }

        messages.info(request, f'Trovate {totale_catene} opportunità di scambio per i tuoi annunci!')

    elif ricerca_eseguita and not ha_annunci:
        # Utente ha cercato ma non ha annunci
        context = {
            'ricerca_eseguita': True,
            'scambi_diretti_alta': [],
            'scambi_diretti_generici': [],
            'catene_alta_qualita': [],
            'catene_generiche': [],
            'totale_scambi_diretti': 0,
            'totale_catene_lunghe': 0,
            'totale_catene': 0,
            'personalizzato': True,
            'nessun_annuncio': True,
        }

        messages.warning(request,
            'Non hai annunci attivi! Pubblica un annuncio per trovare opportunità di scambio.')

    else:
        # Prima visita o utente senza annunci
        context = {
            'ricerca_eseguita': False,
            'personalizzato': True,
            'ha_annunci': ha_annunci,
        }

    return render(request, 'scambi/catene_scambio.html', context)


@login_required
def le_mie_catene(request):
    """Vista ottimizzata per le catene personali dell'utente"""
    import time

    # Controlla se l'utente ha annunci attivi
    annunci_utente = Annuncio.objects.filter(utente=request.user, attivo=True)
    ha_annunci = annunci_utente.exists()

    # Controlla se è stata richiesta una nuova ricerca
    cerca_nuove = request.GET.get('cerca') == 'true'

    # Controlla se è stata richiesta una ricerca per annuncio specifico
    annuncio_id = request.GET.get('annuncio_id')
    annuncio_selezionato = None
    if annuncio_id:
        try:
            annuncio_selezionato = Annuncio.objects.get(id=annuncio_id, utente=request.user, attivo=True)
        except Annuncio.DoesNotExist:
            messages.error(request, 'Annuncio non trovato o non accessibile.')
            annuncio_id = None

    if cerca_nuove and ha_annunci:
        # Import delle funzioni di matching
        from .matching import trova_catene_scambio, trova_scambi_diretti, filtra_catene_per_utente, trova_catene_per_annuncio_ottimizzato

        if annuncio_selezionato:
            print(f"🔍 RICERCA CATENE per annuncio specifico: {annuncio_selezionato.titolo}")
        else:
            print(f"🔍 RICERCA LE MIE CATENE per utente: {request.user.username}")

        try:
            start_time = time.time()
            timeout_seconds = 15  # 15 secondi di timeout (ultra-sicuro)

            # Se è specificato un annuncio, usa la ricerca ottimizzata per annuncio
            if annuncio_selezionato:
                print(f"⏰ Ricerca ottimizzata per annuncio: {annuncio_selezionato.titolo}")
                tutte_catene = trova_catene_per_annuncio_ottimizzato(
                    annuncio_selezionato,
                    max_lunghezza=6,
                    includi_generiche=True
                )
                elapsed = time.time() - start_time
                messages.success(request, f'Ricerca ottimizzata completata in {elapsed:.1f} secondi. Trovate {len(tutte_catene)} catene per "{annuncio_selezionato.titolo}"!')
            else:
                # Esegui ricerca con limitazioni per evitare timeout
                print("⏰ Inizio ricerca scambi diretti...")
                scambi_diretti = trova_scambi_diretti_ottimizzato()

                if time.time() - start_time > timeout_seconds:
                    messages.error(request, 'Ricerca interrotta per timeout. Troppi dati da elaborare.')
                    tutte_catene = scambi_diretti
                else:
                    print("⏰ Inizio ricerca catene lunghe...")
                    try:
                        # Ricerca tutte le catene disponibili nel database
                        catene = trova_catene_scambio_ottimizzato()

                        if time.time() - start_time > timeout_seconds:
                            messages.warning(request, 'Ricerca parziale completata (timeout raggiunto). Mostrando solo scambi diretti.')
                            tutte_catene = scambi_diretti
                        else:
                            # Separa catene per qualità
                            catene_alta_qualita = [c for c in catene if c.get('categoria_qualita') == 'alta']
                            catene_generiche = [c for c in catene if c.get('categoria_qualita') == 'generica']

                            # Filtra tutto per l'utente attuale
                            scambi_diretti_utente, catene_lunghe_utente = filtra_catene_per_utente_ottimizzato(
                                scambi_diretti, catene_alta_qualita + catene_generiche, request.user
                            )

                            # Ricomponi le catene filtrate
                            tutte_catene = scambi_diretti_utente + catene_lunghe_utente

                            elapsed = time.time() - start_time
                            messages.success(request, f'Ricerca completata in {elapsed:.1f} secondi. Trovate {len(tutte_catene)} opportunità di scambio per te!')
                    except Exception as e:
                        print(f"Errore durante ricerca catene lunghe: {e}")
                        tutte_catene = scambi_diretti
                        messages.warning(request, 'Errore nella ricerca catene lunghe. Mostrando solo scambi diretti.')

        except Exception as e:
            print(f"Errore generale durante ricerca catene: {e}")
            messages.error(request, 'Errore durante la ricerca delle catene. Riprova più tardi.')
            tutte_catene = []

        # Rimuovi duplicati e organizza
        catene_uniche = []
        combinazioni_viste = set()

        for catena in tutte_catene:
            utenti_ordinati = tuple(sorted(catena['utenti']))
            if utenti_ordinati not in combinazioni_viste:
                combinazioni_viste.add(utenti_ordinati)
                catene_uniche.append(catena)

        # UNIFICATO: Tratta tutte le catene (2-6) allo stesso modo
        # Ordina per qualità
        catene_alta_qualita = [c for c in catene_uniche if c.get('categoria_qualita') == 'alta']
        catene_generiche = [c for c in catene_uniche if c.get('categoria_qualita') == 'generica']

        # Ordina per lunghezza e punteggio
        catene_alta_qualita.sort(key=lambda x: (len(x.get('utenti', [])), -x.get('punteggio_qualita', 0)))
        catene_generiche.sort(key=lambda x: (len(x.get('utenti', [])), -x.get('punteggio_qualita', 0)))

        # Aggiungi flag per i preferiti e hash se l'utente è autenticato
        if request.user.is_authenticated:
            for catena in catene_alta_qualita + catene_generiche:
                catena['is_favorita'] = is_catena_preferita(request.user, catena)
                catena['hash_catena'] = genera_hash_catena(catena)
                # Converti la catena in JSON string per il template
                catena['json_data'] = json.dumps(catena, default=str)

        # Ottieni le catene preferite dell'utente
        catene_preferite_qs = CatenaPreferita.objects.filter(utente=request.user).order_by('-data_aggiunta')
        catene_preferite = processa_catene_preferite(catene_preferite_qs)

        # Template compatibility: unisci le liste
        catene_specifiche = catene_alta_qualita + catene_generiche

        # UNIFICATO: Raggruppa TUTTE le catene (2-6) per numero di partecipanti
        catene_2 = [c for c in catene_specifiche if len(c.get('utenti', [])) == 2]
        catene_3 = [c for c in catene_specifiche if len(c.get('utenti', [])) == 3]
        catene_4 = [c for c in catene_specifiche if len(c.get('utenti', [])) == 4]
        catene_5 = [c for c in catene_specifiche if len(c.get('utenti', [])) == 5]
        catene_6 = [c for c in catene_specifiche if len(c.get('utenti', [])) == 6]

        context = {
            'catene_alta_qualita': catene_alta_qualita,
            'catene_generiche': catene_generiche,
            'catene_preferite': catene_preferite,
            'totale_catene': len(catene_uniche),
            'totale_scambi_diretti': len(catene_2),
            'totale_catene_lunghe': len(catene_uniche) - len(catene_2),
            'totale_specifiche': len(catene_alta_qualita),
            'totale_generiche': len(catene_generiche),
            'ricerca_eseguita': True,
            'personalizzato': True,
            'miei_annunci': annunci_utente,
            'annuncio_selezionato': annuncio_selezionato,
            # Variabili per template
            'catene_specifiche': catene_specifiche,
            'catene_2': catene_2,
            'catene_3': catene_3,
            'catene_4': catene_4,
            'catene_5': catene_5,
            'catene_6': catene_6,
        }

    elif cerca_nuove and not ha_annunci:
        # Utente ha cercato ma non ha annunci
        # Ottieni le catene preferite dell'utente
        catene_preferite_qs = CatenaPreferita.objects.filter(utente=request.user).order_by('-data_aggiunta')
        catene_preferite = processa_catene_preferite(catene_preferite_qs)

        context = {
            'scambi_diretti_alta': [],
            'scambi_diretti_generici': [],
            'catene_alta_qualita': [],
            'catene_generiche': [],
            'catene_preferite': catene_preferite,
            'totale_catene': 0,
            'totale_scambi_diretti': 0,
            'totale_catene_lunghe': 0,
            'ricerca_eseguita': True,
            'personalizzato': True,
            'nessun_annuncio': True,
            'miei_annunci': annunci_utente,
        }
        messages.warning(request, 'Non hai annunci attivi! Pubblica un annuncio per trovare opportunità di scambio.')
    else:
        # Prima visita - mostra interfaccia vuota
        # Ottieni le catene preferite dell'utente
        catene_preferite_qs = CatenaPreferita.objects.filter(utente=request.user).order_by('-data_aggiunta')
        catene_preferite = processa_catene_preferite(catene_preferite_qs)

        context = {
            'ricerca_eseguita': False,
            'personalizzato': True,
            'ha_annunci': ha_annunci,
            'catene_preferite': catene_preferite,
            'miei_annunci': annunci_utente,
        }

    return render(request, 'scambi/catene_scambio.html', context)


# === HELPER FUNCTIONS PER CATENE PREFERITE ===
import hashlib
import json

def processa_catene_preferite(catene_preferite):
    """
    Processa una queryset di catene preferite, gestendo eventuali dati JSON corrotti.
    Rimuove automaticamente le catene con dati non validi dal database.
    """
    catene_preferite_valide = []
    for catena_preferita in catene_preferite:
        try:
            # Assicurati che catena_data sia un dict per il template
            if isinstance(catena_preferita.catena_data, str):
                catena_preferita.catena_data = json.loads(catena_preferita.catena_data)
            # Aggiungi anche la versione JSON per il JavaScript
            catena_preferita.json_data = json.dumps(catena_preferita.catena_data, default=str)
            catene_preferite_valide.append(catena_preferita)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"⚠️ Errore nel parsing dei dati di catena preferita ID {catena_preferita.id}: {e}")
            # Rimuovi la catena preferita corrotta dal database
            try:
                catena_preferita.delete()
                print(f"✅ Catena preferita corrotta ID {catena_preferita.id} rimossa dal database")
            except Exception as delete_error:
                print(f"❌ Errore nella rimozione della catena preferita ID {catena_preferita.id}: {delete_error}")
    return catene_preferite_valide

def riordina_catena_per_utente(catena, utente):
    """
    Riordina la catena in modo che inizi dall'utente specificato.
    Mantiene l'ordine circolare dello scambio, ruotando solo il punto di partenza.
    """
    utenti = catena.get('utenti', [])
    if not utenti:
        return

    # Trova l'indice dell'utente nella lista
    user_index = None
    for i, u in enumerate(utenti):
        if u['user'].id == utente.id:
            user_index = i
            break

    if user_index is None or user_index == 0:
        return  # User not in chain or already first

    # Ruota la lista utenti per far iniziare dall'utente
    catena['utenti'] = utenti[user_index:] + utenti[:user_index]

    # Riordina annunci_coinvolti: ogni utente ha una coppia (offre, cerca)
    # quindi dobbiamo ruotare le COPPIE, non i singoli elementi
    annunci = catena.get('annunci_coinvolti', [])
    if annunci and user_index > 0 and len(annunci) % 2 == 0:
        # Raggruppa annunci in coppie
        coppie = [(annunci[i], annunci[i+1]) for i in range(0, len(annunci), 2)]

        # Ruota le coppie
        coppie_ruotate = coppie[user_index:] + coppie[:user_index]

        # Riappiattisci in lista singola
        catena['annunci_coinvolti'] = [item for coppia in coppie_ruotate for item in coppia]

def genera_hash_catena(catena_data):
    """Genera un hash univoco per una catena basato sui partecipanti e annunci"""
    # Crea una rappresentazione stabile della catena
    # Ordina per ID utente invece di oggetti utente completi
    utenti_data = catena_data.get('utenti', [])
    if utenti_data and isinstance(utenti_data[0], dict):
        # Nuovo formato ottimizzato con dizionari
        utenti = sorted([u['user'].id for u in utenti_data])
    else:
        # Formato legacy con oggetti User diretti
        utenti = sorted([u.id if hasattr(u, 'id') else u for u in utenti_data])
    annunci = []
    for item in catena_data.get('annunci_coinvolti', []):
        # Gestisce sia oggetti Annuncio che dizionari
        annuncio = item.get('annuncio')
        if hasattr(annuncio, 'id'):
            # È un oggetto Annuncio
            annuncio_id = annuncio.id
        elif isinstance(annuncio, dict):
            # È un dizionario
            annuncio_id = annuncio.get('id')
        else:
            # È probabilmente già un ID
            annuncio_id = annuncio

        annunci.append({
            'annuncio_id': annuncio_id,
            'utente': item.get('utente'),
            'ruolo': item.get('ruolo')
        })
    annunci = sorted(annunci, key=lambda x: (x['annuncio_id'], x['utente']))

    # Crea stringa per hash - converte ID in stringhe
    hash_string = f"{'-'.join(map(str, utenti))}:{json.dumps(annunci, sort_keys=True)}"
    return hashlib.md5(hash_string.encode()).hexdigest()

def is_catena_preferita(user, catena_data):
    """Controlla se una catena è già nei preferiti dell'utente"""
    if not user.is_authenticated:
        return False
    catena_hash = genera_hash_catena(catena_data)
    return CatenaPreferita.objects.filter(utente=user, catena_hash=catena_hash).exists()


# === SISTEMA NOTIFICHE E PREFERITI ===

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Preferiti, Notifica, PropostaScambio, CatenaPreferita
from .notifications import (
    notifica_preferito_aggiunto,
    conta_notifiche_non_lette,
    ottieni_notifiche_recenti,
    segna_tutte_come_lette,
    notifica_benvenuto
)


@login_required
@require_POST
def aggiungi_preferito(request, annuncio_id):
    """Vista AJAX per aggiungere/rimuovere un annuncio dai preferiti"""
    annuncio = get_object_or_404(Annuncio, id=annuncio_id, attivo=True)

    # Non può aggiungere i propri annunci ai preferiti
    if annuncio.utente == request.user:
        return JsonResponse({
            'success': False,
            'error': 'Non puoi aggiungere i tuoi annunci ai preferiti'
        })

    preferito, created = Preferiti.objects.get_or_create(
        utente=request.user,
        annuncio=annuncio
    )

    if created:
        # Aggiunto ai preferiti - crea notifica
        notifica_preferito_aggiunto(annuncio, request.user)
        action = 'added'
        message = f'Annuncio "{annuncio.titolo}" aggiunto ai preferiti'
    else:
        # Già nei preferiti - rimuovi
        preferito.delete()
        action = 'removed'
        message = f'Annuncio "{annuncio.titolo}" rimosso dai preferiti'

    return JsonResponse({
        'success': True,
        'action': action,
        'message': message
    })


@login_required
def lista_preferiti(request):
    """Vista per mostrare gli annunci preferiti dell'utente"""
    preferiti = Preferiti.objects.filter(utente=request.user).select_related('annuncio', 'annuncio__utente')

    context = {
        'preferiti': preferiti,
        'total_preferiti': preferiti.count()
    }

    return render(request, 'scambi/lista_preferiti.html', context)


@login_required
@require_POST
def aggiungi_catena_preferita(request):
    """Vista AJAX per aggiungere/rimuovere una catena dai preferiti"""
    try:
        # Recupera i dati della catena dal POST (supporta sia form data che JSON)
        if request.content_type == 'application/json':
            # Dati inviati come JSON nel body
            data = json.loads(request.body)
            catena_data_json = data.get('catena_data')
            catena_hash_directo = data.get('catena_hash')  # Nuovo: accetta hash diretto
        else:
            # Dati inviati come form data
            catena_data_json = request.POST.get('catena_data')
            catena_hash_directo = request.POST.get('catena_hash')

        # Supporta due modi: hash diretto o dati completi
        if catena_hash_directo:
            # Usa l'hash fornito direttamente
            catena_hash = catena_hash_directo
            # Cerca se esiste già questa catena nei preferiti per recuperare i dati
            catena_esistente = CatenaPreferita.objects.filter(
                utente=request.user,
                catena_hash=catena_hash
            ).first()

            if catena_esistente:
                # Catena già nei preferiti - la rimuoviamo
                catena_data = catena_esistente.catena_data
                catena_esistente.delete()
                return JsonResponse({
                    'success': True,
                    'action': 'removed',
                    'message': 'Catena rimossa dai preferiti'
                })
            else:
                # Catena non nei preferiti - dobbiamo ricevere i dati completi per salvarla
                # Fallback ai dati completi se forniti
                if catena_data_json:
                    if isinstance(catena_data_json, str):
                        catena_data = json.loads(catena_data_json)
                    else:
                        catena_data = catena_data_json
                    # TODO: L'hash potrebbe non corrispondere a causa della serializzazione con default=str
                    # Temporaneamente disabilitiamo la validazione dell'hash
                    expected_hash = genera_hash_catena(catena_data)
                    if expected_hash != catena_hash:
                        print(f"DEBUG: Hash mismatch - using catena_data without validation")
                        print(f"DEBUG: expected_hash = {expected_hash}")
                        print(f"DEBUG: received catena_hash = {catena_hash}")
                        # Continuiamo comunque con i dati ricevuti
                else:
                    return JsonResponse({'success': False, 'error': 'Catena non trovata nei preferiti e nessun dato fornito per salvarla'})

        elif catena_data_json:
            # Metodo originale: usa i dati completi
            if isinstance(catena_data_json, str):
                catena_data = json.loads(catena_data_json)
            else:
                catena_data = catena_data_json
            catena_hash = genera_hash_catena(catena_data)
        else:
            return JsonResponse({'success': False, 'error': 'Né hash né dati catena forniti'})

        # A questo punto abbiamo i dati completi, gestiamo aggiunta/rimozione
        catena_preferita, created = CatenaPreferita.objects.get_or_create(
            utente=request.user,
            catena_hash=catena_hash,
            defaults={
                'catena_data': catena_data,
                'tipo_catena': catena_data.get('tipo', 'catena_lunga'),
                'categoria_qualita': catena_data.get('categoria_qualita', 'generica'),
            }
        )

        if created:
            action = 'added'
            message = 'Catena aggiunta ai preferiti!'
        else:
            # Rimuovi dai preferiti
            catena_preferita.delete()
            action = 'removed'
            message = 'Catena rimossa dai preferiti'

        return JsonResponse({
            'success': True,
            'action': action,
            'message': message
        })

    except json.JSONDecodeError as e:
        return JsonResponse({'success': False, 'error': 'Dati catena non validi'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Errore: {str(e)}'})


@login_required
def lista_notifiche(request):
    """Vista per mostrare le notifiche dell'utente"""
    notifiche = Notifica.objects.filter(utente=request.user).select_related('annuncio_collegato', 'utente_collegato')

    context = {
        'notifiche': notifiche,
        'total_notifiche': notifiche.count(),
        'non_lette': notifiche.filter(letta=False).count()
    }

    return render(request, 'scambi/lista_notifiche.html', context)


@login_required
@require_POST
def segna_notifica_letta(request, notifica_id):
    """Vista AJAX per segnare una notifica come letta"""
    notifica = get_object_or_404(Notifica, id=notifica_id, utente=request.user)
    notifica.mark_as_read()

    return JsonResponse({
        'success': True,
        'message': 'Notifica segnata come letta'
    })


@login_required
@require_POST
def segna_tutte_notifiche_lette(request):
    """Vista AJAX per segnare tutte le notifiche come lette"""
    count = segna_tutte_come_lette(request.user)

    return JsonResponse({
        'success': True,
        'message': f'{count} notifiche segnate come lette'
    })


@login_required
def notifica_click_redirect(request, notifica_id):
    """Vista per segnare una notifica come letta e reindirizzare alla destinazione"""
    notifica = get_object_or_404(Notifica, id=notifica_id, utente=request.user)

    # Segna come letta
    if not notifica.letta:
        notifica.mark_as_read()

    # Determina dove reindirizzare
    if notifica.url_azione:
        redirect_url = notifica.url_azione
    else:
        # Fallback alla lista notifiche
        redirect_url = reverse('lista_notifiche')

    return redirect(redirect_url)


def context_processor_notifiche(request):
    """Context processor per aggiungere dati notifiche e chat a tutti i template"""
    if request.user.is_authenticated:
        from .notifications import conta_conversazioni_non_lette, ottieni_preview_conversazioni
        return {
            'notifiche_non_lette': conta_notifiche_non_lette(request.user),
            'notifiche_recenti': ottieni_notifiche_recenti(request.user, 5),
            'conversazioni_non_lette': conta_conversazioni_non_lette(request.user),
            'conversazioni_recenti': ottieni_preview_conversazioni(request.user, 5)
        }
    return {}


# === SISTEMA PROPOSTE DI SCAMBIO ===

from .notifications import notifica_proposta_scambio
from django.utils import timezone


@login_required
def crea_proposta_scambio(request, annuncio_offerto_id, annuncio_richiesto_id):
    """Vista per creare una proposta di scambio"""
    annuncio_offerto = get_object_or_404(Annuncio, id=annuncio_offerto_id, attivo=True)
    annuncio_richiesto = get_object_or_404(Annuncio, id=annuncio_richiesto_id, attivo=True)

    # Verifica che l'utente sia proprietario dell'annuncio offerto
    if annuncio_offerto.utente != request.user:
        messages.error(request, "Puoi proporre solo i tuoi annunci per uno scambio.")
        return redirect('dettaglio_annuncio', annuncio_id=annuncio_richiesto_id)

    # Verifica che non stia proponendo a se stesso
    if annuncio_richiesto.utente == request.user:
        messages.error(request, "Non puoi proporti uno scambio con te stesso.")
        return redirect('dettaglio_annuncio', annuncio_id=annuncio_richiesto_id)

    # Verifica che non esista già una proposta simile in attesa
    proposta_esistente = PropostaScambio.objects.filter(
        richiedente=request.user,
        destinatario=annuncio_richiesto.utente,
        annuncio_offerto=annuncio_offerto,
        annuncio_richiesto=annuncio_richiesto,
        stato='in_attesa'
    ).exists()

    if proposta_esistente:
        messages.warning(request, "Hai già una proposta di scambio in attesa per questi annunci.")
        return redirect('dettaglio_annuncio', annuncio_id=annuncio_richiesto_id)

    if request.method == 'POST':
        messaggio = request.POST.get('messaggio', '')

        # Crea la proposta di scambio
        proposta = PropostaScambio.objects.create(
            richiedente=request.user,
            destinatario=annuncio_richiesto.utente,
            annuncio_offerto=annuncio_offerto,
            annuncio_richiesto=annuncio_richiesto,
            messaggio=messaggio
        )

        # Crea notifica per il destinatario
        notifica_proposta_scambio(proposta)

        messages.success(request, f"Proposta di scambio inviata a {annuncio_richiesto.utente.username}!")
        return redirect('dettaglio_annuncio', annuncio_id=annuncio_richiesto_id)

    context = {
        'annuncio_offerto': annuncio_offerto,
        'annuncio_richiesto': annuncio_richiesto,
    }

    return render(request, 'scambi/crea_proposta_scambio.html', context)


@login_required
def lista_proposte_scambio(request):
    """Vista per mostrare le proposte di scambio dell'utente"""
    proposte_ricevute = PropostaScambio.objects.filter(
        destinatario=request.user
    ).select_related('richiedente', 'annuncio_offerto', 'annuncio_richiesto').order_by('-data_creazione')

    proposte_inviate = PropostaScambio.objects.filter(
        richiedente=request.user
    ).select_related('destinatario', 'annuncio_offerto', 'annuncio_richiesto').order_by('-data_creazione')

    context = {
        'proposte_ricevute': proposte_ricevute,
        'proposte_inviate': proposte_inviate,
        'total_ricevute': proposte_ricevute.count(),
        'total_inviate': proposte_inviate.count(),
    }

    return render(request, 'scambi/lista_proposte_scambio.html', context)


@login_required
@require_POST
def rispondi_proposta_scambio(request, proposta_id):
    """Vista AJAX per rispondere a una proposta di scambio"""
    proposta = get_object_or_404(PropostaScambio, id=proposta_id, destinatario=request.user)

    if proposta.stato != 'in_attesa':
        return JsonResponse({
            'success': False,
            'error': 'Questa proposta è già stata gestita'
        })

    azione = request.POST.get('azione')
    if azione not in ['accetta', 'rifiuta']:
        return JsonResponse({
            'success': False,
            'error': 'Azione non valida'
        })

    if azione == 'accetta':
        proposta.stato = 'accettata'
        messaggio = f"Proposta di scambio accettata! Ora puoi contattare {proposta.richiedente.username} per organizzare lo scambio."
    else:
        proposta.stato = 'rifiutata'
        messaggio = "Proposta di scambio rifiutata."

    proposta.data_risposta = timezone.now()
    proposta.save()

    return JsonResponse({
        'success': True,
        'message': messaggio,
        'nuovo_stato': proposta.get_stato_display()
    })


@login_required
def dettaglio_proposta_scambio(request, proposta_id):
    """Vista per i dettagli di una proposta di scambio"""
    proposta = get_object_or_404(PropostaScambio, id=proposta_id)

    # Verifica che l'utente sia coinvolto nella proposta
    if request.user not in [proposta.richiedente, proposta.destinatario]:
        messages.error(request, "Non hai il permesso di visualizzare questa proposta.")
        return redirect('lista_proposte_scambio')

    context = {
        'proposta': proposta,
        'e_destinatario': request.user == proposta.destinatario,
        'e_richiedente': request.user == proposta.richiedente,
    }

    return render(request, 'scambi/dettaglio_proposta_scambio.html', context)


# === SISTEMA DI RICERCA ===

from django.db.models import Q
from .forms import RicercaAvanzataForm, RicercaVeloceForm


def ricerca_annunci(request):
    """Vista per la ricerca avanzata degli annunci"""
    form = RicercaAvanzataForm(request.GET or None)
    annunci = Annuncio.objects.filter(attivo=True).select_related('utente', 'categoria', 'utente__userprofile')

    # Parametri di ricerca per il template
    ricerca_effettuata = False
    query_originale = ""

    if form.is_valid():
        # Campo di ricerca principale
        q = form.cleaned_data.get('q')
        if q:
            ricerca_effettuata = True
            query_originale = q
            # Cerca nel titolo e nella descrizione
            annunci = annunci.filter(
                Q(titolo__icontains=q) | Q(descrizione__icontains=q)
            )

        # Filtro per tipo
        tipo = form.cleaned_data.get('tipo')
        if tipo:
            ricerca_effettuata = True
            annunci = annunci.filter(tipo=tipo)

        # Filtro per categoria
        categoria = form.cleaned_data.get('categoria')
        if categoria:
            ricerca_effettuata = True
            annunci = annunci.filter(categoria=categoria)

        # Filtro per città
        citta = form.cleaned_data.get('citta')
        if citta:
            ricerca_effettuata = True
            annunci = annunci.filter(utente__userprofile__citta__icontains=citta)

        # Filtro per regione
        regione = form.cleaned_data.get('regione')
        if regione:
            ricerca_effettuata = True
            annunci = annunci.filter(utente__userprofile__regione__icontains=regione)

        # Filtro per prezzo minimo
        prezzo_min = form.cleaned_data.get('prezzo_min')
        if prezzo_min:
            ricerca_effettuata = True
            # Include anche annunci senza prezzo (NULL)
            annunci = annunci.filter(Q(prezzo_stimato__gte=prezzo_min) | Q(prezzo_stimato__isnull=True))

        # Filtro per prezzo massimo
        prezzo_max = form.cleaned_data.get('prezzo_max')
        if prezzo_max:
            ricerca_effettuata = True
            # Include anche annunci senza prezzo (NULL)
            annunci = annunci.filter(Q(prezzo_stimato__lte=prezzo_max) | Q(prezzo_stimato__isnull=True))

        # Filtro per spedizione
        spedizione = form.cleaned_data.get('spedizione')
        if spedizione == 'si':
            ricerca_effettuata = True
            # Annunci che accettano spedizione
            annunci = annunci.filter(metodo_scambio__in=['entrambi', 'spedizione'])
        elif spedizione == 'no':
            ricerca_effettuata = True
            # Solo scambio a mano
            annunci = annunci.filter(metodo_scambio='mano')

        # Filtro per distanza massima
        distanza_max = form.cleaned_data.get('distanza_max')
        if distanza_max and request.user.is_authenticated:
            ricerca_effettuata = True
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                if user_profile.citta_obj:
                    # Filtra annunci entro la distanza specificata
                    from .models import DistanzaCitta
                    annunci_filtrati = []
                    for annuncio in annunci:
                        try:
                            annuncio_profile = annuncio.utente.userprofile
                            if annuncio_profile.citta_obj:
                                distanza = DistanzaCitta.get_distanza(user_profile.citta_obj, annuncio_profile.citta_obj)
                                if distanza is not None and distanza <= distanza_max:
                                    annunci_filtrati.append(annuncio.id)
                        except UserProfile.DoesNotExist:
                            pass
                    annunci = annunci.filter(id__in=annunci_filtrati)
            except UserProfile.DoesNotExist:
                pass

        # Ordinamento
        ordinamento = form.cleaned_data.get('ordinamento', '-data_creazione')
        if ordinamento:
            # Gestisce l'ordinamento per prezzo con NULL values
            if 'prezzo' in ordinamento:
                if ordinamento.startswith('-'):
                    annunci = annunci.order_by(ordinamento, '-data_creazione')
                else:
                    annunci = annunci.order_by(ordinamento, 'data_creazione')
            else:
                annunci = annunci.order_by(ordinamento)

    # Se non è stata effettuata nessuna ricerca, mostra gli annunci più recenti
    if not ricerca_effettuata:
        annunci = annunci.order_by('-data_creazione')

    # Paginazione
    from django.core.paginator import Paginator
    paginator = Paginator(annunci, 12)  # 12 annunci per pagina
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'annunci': page_obj,
        'ricerca_effettuata': ricerca_effettuata,
        'query_originale': query_originale,
        'total_risultati': annunci.count(),
        'paginator': paginator,
        'page_obj': page_obj,
    }

    return render(request, 'scambi/ricerca_annunci.html', context)


def ricerca_veloce(request):
    """Vista per la ricerca veloce dalla navbar"""
    query = request.GET.get('q', '').strip()

    if query:
        # Redirect alla ricerca avanzata con il parametro q
        from django.urls import reverse
        from urllib.parse import urlencode
        url = reverse('ricerca_annunci')
        params = urlencode({'q': query})
        return redirect(f"{url}?{params}")
    else:
        # Se non c'è query, vai alla pagina di ricerca vuota
        return redirect('ricerca_annunci')


# === SISTEMA MESSAGGISTICA ===

from .models import Conversazione, Messaggio, LetturaMessaggio, CatenaScambio
from django.db.models import Q, Prefetch


@login_required
def lista_messaggi(request):
    """Vista per mostrare tutte le conversazioni dell'utente"""
    try:
        conversazioni = Conversazione.objects.filter(
            utenti=request.user,
            attiva=True
        ).prefetch_related(
            'utenti',
            Prefetch('messaggi', queryset=Messaggio.objects.order_by('-data_invio')[:1])
        ).order_by('-data_creazione')  # Usa data_creazione invece di ultimo_messaggio

        context = {
            'conversazioni': conversazioni,
        }
        return render(request, 'scambi/lista_messaggi.html', context)

    except Exception as e:
        # Log dell'errore per debug
        print(f"Errore in lista_messaggi: {e}")
        # Fallback semplice
        conversazioni = Conversazione.objects.filter(
            utenti=request.user,
            attiva=True
        ).order_by('-data_creazione')

        context = {
            'conversazioni': conversazioni,
        }
        return render(request, 'scambi/lista_messaggi.html', context)


@login_required
def chat_conversazione(request, conversazione_id):
    """Vista per visualizzare e inviare messaggi in una conversazione"""
    conversazione = get_object_or_404(
        Conversazione,
        id=conversazione_id,
        utenti=request.user,
        attiva=True
    )

    # Segna tutti i messaggi come letti
    messaggi_non_letti = conversazione.messaggi.exclude(letto_da=request.user)
    for messaggio in messaggi_non_letti:
        messaggio.mark_as_read(request.user)

    # Invia nuovo messaggio
    if request.method == 'POST':
        contenuto = request.POST.get('contenuto', '').strip()
        if contenuto:
            messaggio = Messaggio.objects.create(
                conversazione=conversazione,
                mittente=request.user,
                contenuto=contenuto
            )

            # Aggiorna timestamp conversazione
            conversazione.ultimo_messaggio = timezone.now()
            conversazione.save()

            # Non creiamo più notifiche per i messaggi - il badge sulla chat è sufficiente

            messages.success(request, 'Messaggio inviato!')
            return redirect('chat_conversazione', conversazione_id=conversazione.id)

    # Carica messaggi
    messaggi = conversazione.messaggi.select_related('mittente').prefetch_related('letto_da').order_by('data_invio')

    context = {
        'conversazione': conversazione,
        'messaggi': messaggi,
        'altri_utenti': conversazione.get_altri_utenti(request.user),
    }

    return render(request, 'scambi/chat_conversazione.html', context)


@login_required
def inizia_conversazione(request, username):
    """Vista per iniziare una conversazione privata con un utente"""
    destinatario = get_object_or_404(User, username=username)

    if destinatario == request.user:
        messages.error(request, "Non puoi avviare una conversazione con te stesso.")
        return redirect('lista_messaggi')

    # Verifica se esiste già una conversazione tra i due utenti
    conversazione_esistente = Conversazione.objects.filter(
        tipo='privata',
        utenti=request.user
    ).filter(
        utenti=destinatario
    ).first()

    if conversazione_esistente:
        return redirect('chat_conversazione', conversazione_id=conversazione_esistente.id)

    # Crea nuova conversazione
    conversazione = Conversazione.objects.create(tipo='privata')
    conversazione.utenti.add(request.user, destinatario)

    messages.success(request, f'Conversazione avviata con {destinatario.username}')
    return redirect('chat_conversazione', conversazione_id=conversazione.id)


@login_required
def lista_catene_attivabili(request):
    """Vista per mostrare le catene che l'utente può attivare"""
    # Trova le catene in stato "proposta" che coinvolgono l'utente
    catene_attivabili = CatenaScambio.objects.filter(
        stato='proposta',
        partecipanti=request.user
    ).prefetch_related('partecipanti').order_by('-data_creazione')

    context = {
        'catene_attivabili': catene_attivabili,
        'total_catene': catene_attivabili.count(),
    }

    return render(request, 'scambi/lista_catene_attivabili.html', context)


@login_required
@require_POST
def attiva_catena(request, catena_id):
    """Vista per attivare una catena di scambio"""
    catena = get_object_or_404(CatenaScambio, catena_id=catena_id, partecipanti=request.user)

    if catena.stato != 'proposta':
        return JsonResponse({
            'success': False,
            'error': 'Questa catena non può essere attivata'
        })

    try:
        # Attiva la catena (il metodo gestisce creazione chat e notifiche)
        catena.attiva_catena(request.user)

        return JsonResponse({
            'success': True,
            'message': f'Catena "{catena.nome}" attivata con successo!',
            'chat_url': reverse('chat_conversazione', kwargs={'conversazione_id': catena.conversazione.id}) if catena.conversazione else None
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Errore durante l\'attivazione: {str(e)}'
        })


@login_required
def dettaglio_catena(request, catena_id):
    """Vista per visualizzare i dettagli di una catena di scambio"""
    catena = get_object_or_404(CatenaScambio, catena_id=catena_id, partecipanti=request.user)

    # Ottieni le partecipazioni per mostrare i dettagli degli scambi
    partecipazioni = catena.partecipazionescambio_set.select_related(
        'utente', 'annuncio_da_dare', 'annuncio_da_ricevere'
    ).all()

    context = {
        'catena': catena,
        'partecipazioni': partecipazioni,
        'e_attivatore': catena.utente_attivatore == request.user,
        'puo_attivare': catena.stato == 'proposta',
    }

    return render(request, 'scambi/dettaglio_catena.html', context)


@login_required
def verifica_conversazione_esistente(request, user_id):
    """API endpoint per verificare se esiste già una conversazione con un utente"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Metodo non supportato'}, status=405)

    try:
        destinatario = get_object_or_404(User, id=user_id)

        if destinatario == request.user:
            return JsonResponse({'error': 'Non puoi avviare una conversazione con te stesso'}, status=400)

        # Verifica se esiste già una conversazione tra i due utenti
        conversazione_esistente = Conversazione.objects.filter(
            tipo='privata',
            utenti=request.user
        ).filter(
            utenti=destinatario
        ).first()

        if conversazione_esistente:
            return JsonResponse({
                'conversazione_esistente': True,
                'conversazione_id': conversazione_esistente.id
            })
        else:
            return JsonResponse({
                'conversazione_esistente': False
            })

    except Exception as e:
        return JsonResponse({'error': 'Errore del server'}, status=500)


@login_required
def invia_messaggio_da_annuncio(request):
    """API endpoint per inviare un messaggio riguardo a un annuncio"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo non supportato'}, status=405)

    try:
        data = json.loads(request.body)
        destinatario_id = data.get('destinatario_id')
        messaggio_testo = data.get('messaggio', '').strip()
        annuncio_id = data.get('annuncio_id')

        if not messaggio_testo:
            return JsonResponse({'error': 'Il messaggio non può essere vuoto'}, status=400)

        destinatario = get_object_or_404(User, id=destinatario_id)
        annuncio = get_object_or_404(Annuncio, id=annuncio_id)

        if destinatario == request.user:
            return JsonResponse({'error': 'Non puoi inviare un messaggio a te stesso'}, status=400)

        # Verifica se esiste già una conversazione
        conversazione = Conversazione.objects.filter(
            tipo='privata',
            utenti=request.user
        ).filter(
            utenti=destinatario
        ).first()

        # Se non esiste, creala
        if not conversazione:
            conversazione = Conversazione.objects.create(tipo='privata')
            conversazione.utenti.add(request.user, destinatario)

        # Crea il messaggio con riferimento all'annuncio
        messaggio_contenuto = f"Riguardo all'annuncio '{annuncio.titolo}':\n\n{messaggio_testo}"

        messaggio = Messaggio.objects.create(
            conversazione=conversazione,
            mittente=request.user,
            contenuto=messaggio_contenuto
        )

        # Aggiorna timestamp conversazione
        conversazione.ultimo_messaggio = timezone.now()
        conversazione.save()

        # Non creiamo più notifiche per i messaggi - il badge sulla chat è sufficiente

        return JsonResponse({
            'success': True,
            'conversazione_id': conversazione.id,
            'messaggio': 'Messaggio inviato con successo!'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Dati JSON non validi'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Errore del server'}, status=500)


# === API SISTEMA CALCOLO CICLI SEPARATO ===

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .models import CicloScambio
import time


@require_http_methods(["GET"])
@login_required
def api_cicli_utente(request, user_id):
    """
    API endpoint per ottenere i cicli di scambio per un utente specifico
    Performance target: < 50ms
    """
    start_time = time.time()

    try:
        # Verifica che l'utente possa accedere ai propri cicli
        if request.user.id != user_id and not request.user.is_staff:
            return JsonResponse({
                'error': 'Non autorizzato'
            }, status=403)

        # Query ottimizzata per trovare cicli dell'utente
        limit = min(int(request.GET.get('limit', 50)), 100)  # Max 100 cicli
        offset = int(request.GET.get('offset', 0))

        # Usa il metodo ottimizzato del model
        cicli_queryset = CicloScambio.find_for_user(user_id, limit + offset)[offset:offset + limit]
        cicli_data = [ciclo.to_dict() for ciclo in cicli_queryset]

        # Statistiche totali
        cicli_totali = CicloScambio.objects.filter(valido=True).count()
        ultimo_aggiornamento = CicloScambio.objects.filter(valido=True).order_by('-calcolato_at').first()

        response_data = {
            'success': True,
            'cicli': cicli_data,
            'total': len(cicli_data),
            'cicli_totali_sistema': cicli_totali,
            'ultimo_aggiornamento': ultimo_aggiornamento.calcolato_at.isoformat() if ultimo_aggiornamento else None,
            'performance': {
                'query_time_ms': round((time.time() - start_time) * 1000, 2),
                'cache_hit': True  # Sempre True dato che leggiamo dal DB pre-calcolato
            },
            'pagination': {
                'limit': limit,
                'offset': offset,
                'has_more': len(cicli_data) == limit
            }
        }

        # Aggiungi header per caching (5 minuti)
        response = JsonResponse(response_data)
        response['Cache-Control'] = 'public, max-age=300'
        response['X-Performance-Ms'] = str(round((time.time() - start_time) * 1000, 2))

        return response

    except Exception as e:
        return JsonResponse({
            'error': 'Errore del server',
            'message': str(e)
        }, status=500)


@require_http_methods(["GET"])
def api_cicli_stats(request):
    """
    API endpoint per statistiche generali sui cicli
    Accessibile pubblicamente per dashboard
    """
    start_time = time.time()

    try:
        # Query ottimizzate per statistiche
        stats = {
            'cicli_totali': CicloScambio.objects.filter(valido=True).count(),
            'cicli_per_lunghezza': {},
            'ultimo_calcolo': None,
            'sistema_attivo': True
        }

        # Statistiche per lunghezza ciclo
        for lunghezza in range(2, 7):  # 2-6 utenti
            count = CicloScambio.objects.filter(valido=True, lunghezza=lunghezza).count()
            stats['cicli_per_lunghezza'][f'{lunghezza}_utenti'] = count

        # Ultimo calcolo
        ultimo_ciclo = CicloScambio.objects.filter(valido=True).order_by('-calcolato_at').first()
        if ultimo_ciclo:
            stats['ultimo_calcolo'] = ultimo_ciclo.calcolato_at.isoformat()

        response_data = {
            'success': True,
            'stats': stats,
            'performance': {
                'query_time_ms': round((time.time() - start_time) * 1000, 2)
            }
        }

        # Caching più aggressivo per stats (15 minuti)
        response = JsonResponse(response_data)
        response['Cache-Control'] = 'public, max-age=900'
        response['X-Performance-Ms'] = str(round((time.time() - start_time) * 1000, 2))

        return response

    except Exception as e:
        return JsonResponse({
            'error': 'Errore del server',
            'message': str(e)
        }, status=500)



# === WEBHOOK SYSTEM FOR FREE CYCLE CALCULATION ===

@csrf_exempt
@require_POST
def webhook_calcola_cicli(request):
    """
    Webhook endpoint per calcolare i cicli da servizio esterno
    Alternativa gratuita al cron job di Render
    """
    import time
    try:
        # Verifica autorizzazione con secret token
        webhook_secret = os.environ.get("POLYGONUM_WEBHOOK_SECRET", "default-secret-change-me")

        # Verifica header Authorization
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Missing or invalid authorization header"}, status=401)

        token = auth_header[7:]  # Rimuove "Bearer "
        if token != webhook_secret:
            return JsonResponse({"error": "Invalid webhook secret"}, status=401)

        # Importa il comando di calcolo cicli
        from django.core.management import call_command
        from io import StringIO
        import sys

        # Cattura l'output del comando
        output_buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output_buffer

        start_time = time.time()

        # Esegui il comando di calcolo cicli con verbosità ridotta per webhook
        call_command(
            "calcola_cicli",
            max_length=6,
            commit_batch_size=50,
            cleanup_old=True,
            verbosity=0  # Ridotto a 0 per evitare output troppo verboso nel webhook
        )

        # Ripristina stdout
        sys.stdout = old_stdout
        command_output = output_buffer.getvalue()

        # Statistiche finali
        from .models import CicloScambio
        cicli_totali = CicloScambio.objects.count()
        cicli_validi = CicloScambio.objects.filter(valido=True).count()

        execution_time = time.time() - start_time

        # Estrai solo statistiche essenziali dall'output per evitare risposte troppo grandi
        output_lines = command_output.split('\n')
        summary_lines = [line for line in output_lines if any(keyword in line for keyword in [
            'trovati', 'salvati', 'rimossi', 'completato', 'tempo', 'performance', '✅', '📊'
        ])]

        return JsonResponse({
            "success": True,
            "message": "Calcolo cicli completato con successo",
            "stats": {
                "cicli_totali": cicli_totali,
                "cicli_validi": cicli_validi,
                "execution_time_seconds": round(execution_time, 2)
            },
            "summary": summary_lines[-10:] if summary_lines else ["Calcolo completato"],  # Solo ultimi 10 righe rilevanti
            "timestamp": time.time()
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": "Errore durante il calcolo cicli",
            "message": str(e),
            "timestamp": time.time()
        }, status=500)


# === SISTEMA PROPOSTE CATENE MVP ===

@login_required
@require_POST
def proponi_catena(request, ciclo_id):
    """Vista AJAX per proporre/annullare interesse a una catena di scambio (toggle)"""
    try:
        ciclo = get_object_or_404(CicloScambio, id=ciclo_id, valido=True)

        # Verifica che l'utente sia coinvolto nella catena
        if request.user.id not in ciclo.users:
            return JsonResponse({
                'success': False,
                'error': 'Non fai parte di questa catena'
            })

        # Cerca se esiste già una proposta per questo ciclo
        proposta_esistente = PropostaCatena.objects.filter(ciclo=ciclo).first()

        if proposta_esistente:
            # Esiste già una proposta, gestisci il toggle dell'interesse dell'utente
            try:
                risposta_obj = RispostaProposta.objects.get(
                    proposta=proposta_esistente,
                    utente=request.user
                )

                # Toggle: se interessato → rimuovi interesse, se non interessato/in_attesa → aggiungi interesse
                if risposta_obj.risposta == 'interessato':
                    # Annulla interesse
                    risposta_obj.risposta = 'non_interessato'
                    risposta_obj.save()

                    # Se l'utente è l'iniziatore, annulla tutta la proposta
                    if proposta_esistente.iniziatore == request.user:
                        proposta_esistente.stato = 'annullata'
                        proposta_esistente.save()

                    return JsonResponse({
                        'success': True,
                        'action': 'removed',
                        'message': 'Interesse rimosso',
                        'count_interessati': proposta_esistente.get_count_interessati(),
                        'count_totale': proposta_esistente.get_count_totale()
                    })
                else:
                    # Aggiungi interesse
                    risposta_obj.risposta = 'interessato'
                    risposta_obj.data_risposta = timezone.now()
                    risposta_obj.save()

                    # Verifica se tutti sono interessati
                    count_interessati = proposta_esistente.get_count_interessati()
                    count_totale = proposta_esistente.get_count_totale()
                    tutti_interessati = count_interessati == count_totale

                    if tutti_interessati:
                        # Aggiorna stato proposta
                        proposta_esistente.stato = 'tutti_interessati'
                        proposta_esistente.save()

                        # Crea chat di gruppo
                        from .models import Conversazione, Messaggio
                        from django.contrib.auth.models import User

                        utenti_coinvolti = User.objects.filter(id__in=ciclo.users)

                        # Crea conversazione di gruppo
                        conversazione = Conversazione.objects.create(
                            tipo='gruppo',
                            nome=f"Catena di scambio #{ciclo.id}",
                            catena_scambio_id=str(ciclo.id)
                        )
                        conversazione.utenti.set(utenti_coinvolti)

                        # Messaggio di sistema
                        Messaggio.objects.create(
                            conversazione=conversazione,
                            mittente=request.user,
                            contenuto=f"🎉 Tutti sono interessati! Catena attivata. Coordinate gli scambi qui.",
                            is_sistema=True
                        )

                        # Invia notifiche a tutti
                        from .notifications import notifica_tutti_interessati
                        for utente in utenti_coinvolti:
                            notifica_tutti_interessati(utente, proposta_esistente)

                    response_data = {
                        'success': True,
                        'action': 'added',
                        'message': 'Interesse confermato!',
                        'count_interessati': count_interessati,
                        'count_totale': count_totale,
                        'tutti_interessati': tutti_interessati
                    }

                    # Se tutti sono interessati, aggiungi info sulla chat creata
                    if tutti_interessati:
                        response_data['chat_creata'] = True
                        response_data['chat_id'] = conversazione.id
                        response_data['redirect_url'] = reverse('lista_messaggi')

                    return JsonResponse(response_data)
            except RispostaProposta.DoesNotExist:
                # L'utente non ha ancora una risposta, creala
                RispostaProposta.objects.create(
                    proposta=proposta_esistente,
                    utente=request.user,
                    risposta='interessato',
                    data_risposta=timezone.now()
                )

                # Verifica se tutti sono interessati
                count_interessati = proposta_esistente.get_count_interessati()
                count_totale = proposta_esistente.get_count_totale()
                tutti_interessati = count_interessati == count_totale

                if tutti_interessati:
                    # Aggiorna stato proposta
                    proposta_esistente.stato = 'tutti_interessati'
                    proposta_esistente.save()

                    # Crea chat di gruppo
                    from .models import Conversazione, Messaggio
                    from django.contrib.auth.models import User

                    utenti_coinvolti = User.objects.filter(id__in=ciclo.users)

                    # Crea conversazione di gruppo
                    conversazione = Conversazione.objects.create(
                        tipo='gruppo',
                        nome=f"Catena di scambio #{ciclo.id}",
                        catena_scambio_id=str(ciclo.id)
                    )
                    conversazione.utenti.set(utenti_coinvolti)

                    # Messaggio di sistema
                    Messaggio.objects.create(
                        conversazione=conversazione,
                        mittente=request.user,
                        contenuto=f"🎉 Tutti sono interessati! Catena attivata. Coordinate gli scambi qui.",
                        is_sistema=True
                    )

                    # Invia notifiche a tutti
                    from .notifications import notifica_tutti_interessati
                    for utente in utenti_coinvolti:
                        notifica_tutti_interessati(utente, proposta_esistente)

                response_data = {
                    'success': True,
                    'action': 'added',
                    'message': 'Interesse confermato!',
                    'count_interessati': count_interessati,
                    'count_totale': count_totale,
                    'tutti_interessati': tutti_interessati
                }

                # Se tutti sono interessati, aggiungi info sulla chat creata
                if tutti_interessati:
                    response_data['chat_creata'] = True
                    response_data['chat_id'] = conversazione.id
                    response_data['redirect_url'] = reverse('lista_messaggi')

                return JsonResponse(response_data)
        else:
            # Nessuna proposta esistente, crea nuova proposta
            proposta = PropostaCatena.objects.create(
                ciclo=ciclo,
                iniziatore=request.user
            )

            # Crea le risposte per tutti gli utenti coinvolti
            from django.contrib.auth.models import User
            utenti_coinvolti = User.objects.filter(id__in=ciclo.users)

            for utente in utenti_coinvolti:
                RispostaProposta.objects.create(
                    proposta=proposta,
                    utente=utente,
                    risposta='interessato' if utente == request.user else 'in_attesa'
                )

            # Invia notifiche agli altri utenti
            from .notifications import notifica_proposta_catena
            altri_utenti = utenti_coinvolti.exclude(id=request.user.id)
            for utente in altri_utenti:
                notifica_proposta_catena(utente, proposta, request.user)

            return JsonResponse({
                'success': True,
                'action': 'added',
                'message': f'Proposta inviata a {altri_utenti.count()} utenti!',
                'proposta_id': proposta.id,
                'count_interessati': 1,
                'count_totale': len(ciclo.users)
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_POST  
def rispondi_proposta_catena(request, proposta_id):
    """Vista AJAX per rispondere a una proposta di catena (MVP)"""
    try:
        proposta = get_object_or_404(PropostaCatena, id=proposta_id)
        
        # Verifica che l'utente sia coinvolto
        risposta_obj = get_object_or_404(
            RispostaProposta,
            proposta=proposta,
            utente=request.user
        )
        
        azione = request.POST.get('azione')  # 'interessato' o 'non_interessato'
        
        if azione == 'interessato':
            risposta_obj.segna_interessato()
            message = 'Hai confermato il tuo interesse!'
            
            # Controlla se tutti sono interessati
            if proposta.stato == 'tutti_interessati':
                # Notifica a tutti che la catena è pronta
                from .notifications import notifica_tutti_interessati
                utenti = proposta.get_utenti_coinvolti()
                for utente in utenti:
                    notifica_tutti_interessati(utente, proposta)
                    
                message = '🎉 Tutti sono interessati! Contattatevi per organizzare lo scambio.'
            else:
                # Notifica agli altri che qualcuno ha risposto
                from .notifications import notifica_risposta_proposta
                utenti = proposta.get_utenti_coinvolti().exclude(id=request.user.id)
                for utente in utenti:
                    notifica_risposta_proposta(utente, proposta, request.user, True)
                    
        elif azione == 'non_interessato':
            risposta_obj.segna_non_interessato()
            message = 'Proposta rifiutata'
            
            # Notifica a tutti che la proposta è stata rifiutata
            from .notifications import notifica_risposta_proposta
            utenti = proposta.get_utenti_coinvolti().exclude(id=request.user.id)
            for utente in utenti:
                notifica_risposta_proposta(utente, proposta, request.user, False)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Azione non valida'
            })
        
        return JsonResponse({
            'success': True,
            'message': message,
            'stato': proposta.stato,
            'count_interessati': proposta.get_count_interessati(),
            'count_totale': proposta.get_count_totale()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def stato_proposta_catena(request, ciclo_id):
    """Vista per ottenere lo stato di una proposta per una catena (MVP)"""
    try:
        ciclo = get_object_or_404(CicloScambio, id=ciclo_id, valido=True)
        
        # Cerca proposta attiva per questa catena
        proposta = PropostaCatena.objects.filter(
            ciclo=ciclo,
            stato__in=['in_attesa', 'tutti_interessati']
        ).first()
        
        if not proposta:
            return JsonResponse({
                'has_proposta': False
            })
        
        # Ottieni la risposta dell'utente corrente
        mia_risposta = None
        try:
            risposta_obj = RispostaProposta.objects.get(
                proposta=proposta,
                utente=request.user
            )
            mia_risposta = risposta_obj.risposta
        except RispostaProposta.DoesNotExist:
            pass
        
        return JsonResponse({
            'has_proposta': True,
            'proposta_id': proposta.id,
            'iniziatore': proposta.iniziatore.username,
            'stato': proposta.stato,
            'count_interessati': proposta.get_count_interessati(),
            'count_totale': proposta.get_count_totale(),
            'mia_risposta': mia_risposta,
            'giorni_scadenza': proposta.giorni_alla_scadenza() if proposta.data_scadenza else None,
            'data_scadenza': proposta.data_scadenza.isoformat() if proposta.data_scadenza else None
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def mie_proposte_catene(request):
    """
    Mostra tutte le catene a cui l'utente ha mostrato interesse
    con lo stato di avanzamento dei partecipanti
    """
    # Trova tutte le risposte dell'utente dove ha mostrato interesse
    mie_risposte = RispostaProposta.objects.filter(
        utente=request.user,
        risposta__in=['interessato', 'in_attesa']
    ).select_related('proposta', 'proposta__ciclo', 'proposta__iniziatore')

    # Raggruppa per proposta/ciclo
    catene_info = []
    for risposta in mie_risposte:
        proposta = risposta.proposta
        ciclo = proposta.ciclo

        # Salta proposte annullate o rifiutate
        if proposta.stato in ['annullata', 'rifiutata']:
            continue

        # Calcola stato avanzamento
        count_interessati = proposta.get_count_interessati()
        count_totale = proposta.get_count_totale()
        percentuale = int((count_interessati / count_totale) * 100) if count_totale > 0 else 0

        # Determina lo stato testuale
        if proposta.stato == 'confermata':
            stato_display = 'Confermata'
            stato_class = 'success'
        elif proposta.stato == 'in_attesa':
            if count_interessati == count_totale:
                stato_display = 'Tutti interessati!'
                stato_class = 'success'
            else:
                stato_display = f'In attesa ({count_interessati}/{count_totale})'
                stato_class = 'warning'
        else:
            stato_display = proposta.stato.title()
            stato_class = 'secondary'

        # Ottieni gli scambi dal campo dettagli del ciclo e costruisci il formato atteso dal template
        exchanges = []
        if ciclo and ciclo.dettagli and 'scambi' in ciclo.dettagli:
            from django.contrib.auth.models import User

            for scambio in ciclo.dettagli['scambi']:
                da_user_id = scambio.get('da_user')
                a_user_id = scambio.get('a_user')

                # Ottieni gli utenti
                try:
                    giver = User.objects.get(id=da_user_id)
                    receiver = User.objects.get(id=a_user_id)
                except User.DoesNotExist:
                    continue

                # Processa ogni oggetto scambiato
                for oggetto in scambio.get('oggetti', []):
                    offerto_data = oggetto.get('offerto', {})
                    richiesto_data = oggetto.get('richiesto', {})

                    # Ottieni gli annunci
                    try:
                        giving_ad = Annuncio.objects.get(id=offerto_data.get('id'))
                        receiving_ad = Annuncio.objects.get(id=richiesto_data.get('id'))

                        # Crea l'oggetto exchange nel formato atteso dal template
                        exchange = type('Exchange', (), {
                            'giver': giver,
                            'receiver': receiver,
                            'giving_ad': giving_ad,
                            'receiving_ad': receiving_ad,
                        })()
                        exchanges.append(exchange)
                    except Annuncio.DoesNotExist:
                        continue

        catene_info.append({
            'proposta': proposta,
            'ciclo': ciclo,
            'exchanges': exchanges,
            'mia_risposta': risposta.risposta,
            'count_interessati': count_interessati,
            'count_totale': count_totale,
            'percentuale': percentuale,
            'stato_display': stato_display,
            'stato_class': stato_class,
            'giorni_scadenza': proposta.giorni_alla_scadenza() if proposta.data_scadenza else None,
            'stato_ordinamento': 0 if proposta.stato == 'tutti_interessati' else (1 if proposta.stato == 'in_attesa' else 2)
        })

    # Ordina per stato (tutti_interessati, in_attesa, altro) e poi per data creazione
    catene_info.sort(key=lambda x: (x['stato_ordinamento'], -x['proposta'].data_creazione.timestamp()))

    # Raggruppa per stato per visualizzazione
    catene_per_stato = {
        'tutti_interessati': [c for c in catene_info if c['stato_class'] == 'success' and c['percentuale'] == 100],
        'in_attesa': [c for c in catene_info if c['stato_class'] == 'warning'],
        'altro': [c for c in catene_info if c not in catene_info if c['stato_class'] not in ['success', 'warning']]
    }

    context = {
        'catene_info': catene_info,
        'catene_per_stato': catene_per_stato,
        'total_catene': len(catene_info),
    }

    return render(request, 'scambi/mie_proposte_catene.html', context)


# === SISTEMA PREMIUM ===

def pricing(request):
    """Pagina dei prezzi e piani"""
    return render(request, 'scambi/pricing.html')


@login_required
def premium_checkout(request):
    """Pagina di checkout per Premium con PayPal"""
    profilo = request.user.userprofile
    
    # Se già premium, redirect al profilo
    if profilo.is_premium:
        messages.info(request, 'Sei già un utente Premium!')
        return redirect('profilo_utente', username=request.user.username)
    
    context = {
        'profilo': profilo,
        # Queste verranno da settings/env in produzione
        'paypal_client_id': settings.PAYPAL_CLIENT_ID if hasattr(settings, 'PAYPAL_CLIENT_ID') else 'sandbox',
        'paypal_mode': settings.PAYPAL_MODE if hasattr(settings, 'PAYPAL_MODE') else 'sandbox',
    }
    
    return render(request, 'scambi/premium_checkout.html', context)


@login_required
def premium_success(request):
    """Callback di successo da PayPal"""
    # In produzione, qui verificheresti il pagamento con PayPal API
    # Per ora, attiviamo direttamente il premium
    
    profilo = request.user.userprofile
    profilo.is_premium = True
    
    # Imposta scadenza a 1 mese da ora (per abbonamento mensile)
    from datetime import timedelta
    profilo.premium_scadenza = timezone.now() + timedelta(days=30)
    profilo.save()
    
    messages.success(request, '🎉 Benvenuto in Premium! Il tuo account è stato aggiornato con successo!')
    
    return render(request, 'scambi/premium_success.html', {
        'profilo': profilo
    })


@login_required
def premium_cancel(request):
    """Callback di cancellazione da PayPal"""
    messages.warning(request, 'Upgrade a Premium cancellato. Puoi riprovare quando vuoi!')
    return redirect('pricing')
