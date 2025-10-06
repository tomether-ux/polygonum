from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import UserCreationForm  # Se usi il form base
from django.shortcuts import render
from django.http import HttpResponse
from .matching import trova_catene_scambio, trova_scambi_diretti, filtra_catene_per_utente
from .models import Annuncio
import importlib
from . import matching

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
    catene = trova_catene_scambio()

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
    if request.method == 'POST':
        form = AnnuncioForm(request.POST, request.FILES)  # Aggiungi request.FILES
        if form.is_valid():
            annuncio = form.save(commit=False)
            annuncio.utente = request.user
            annuncio.save()
            messages.success(request, 'Annuncio creato con successo!')
            return redirect('lista_annunci')
    else:
        form = AnnuncioForm()
    
    return render(request, 'scambi/crea_annuncio.html', {'form': form})

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

    if cerca_nuove:
        import time

        # Import delle funzioni di matching
        from .matching import trova_catene_scambio, trova_scambi_diretti, filtra_catene_per_utente

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

                    # Esegui ricerca con limitazioni per evitare timeout
                    print("⏰ Inizio ricerca scambi diretti...")
                    scambi_diretti = trova_scambi_diretti()

                    if time.time() - start_time > timeout_seconds:
                        messages.error(request, 'Ricerca interrotta per timeout. Troppi dati da elaborare.')
                        tutte_catene = scambi_diretti
                    else:
                        print("⏰ Inizio ricerca catene lunghe (limitata a 3 utenti)...")
                        try:
                            # Limita la ricerca delle catene a max 3 utenti per velocizzare
                            catene = trova_catene_scambio(max_lunghezza=3)

                            if time.time() - start_time > timeout_seconds:
                                messages.warning(request, 'Ricerca parziale completata (timeout raggiunto). Mostrando solo scambi diretti.')
                                tutte_catene = scambi_diretti
                            else:
                                # Separa catene per qualità
                                catene_alta_qualita = [c for c in catene if c.get('categoria_qualita') == 'alta']
                                catene_generiche = [c for c in catene if c.get('categoria_qualita') == 'generica']

                                # Filtra tutto per l'utente attuale
                                scambi_diretti_utente, catene_lunghe_utente = filtra_catene_per_utente(
                                    scambi_diretti, catene_alta_qualita + catene_generiche, request.user
                                )

                                # Ricomponi le catene filtrate
                                tutte_catene = scambi_diretti_utente + catene_lunghe_utente

                                elapsed = time.time() - start_time
                                messages.success(request, f'Ricerca completata in {elapsed:.1f} secondi. Trovate {len(tutte_catene)} opportunità di scambio!')
                        except Exception as e:
                            print(f"Errore durante ricerca catene lunghe: {e}")
                            tutte_catene = scambi_diretti
                            messages.warning(request, 'Errore nella ricerca catene lunghe. Mostrando solo scambi diretti.')
                else:
                    tutte_catene = []
                    messages.warning(request, 'Non hai annunci attivi! Pubblica un annuncio per partecipare agli scambi.')
            else:
                # Utente non autenticato - ricerca molto limitata
                print("🔍 Ricerca per utente non autenticato (limitata a scambi diretti)")
                try:
                    scambi_diretti = trova_scambi_diretti()
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
        # Se non è stata richiesta ricerca, mostra risultati vuoti o cached
        print("📋 Visualizzazione catene senza ricerca")
        tutte_catene = []

    # Rimuovi duplicati
    catene_uniche = []
    combinazioni_viste = set()

    for catena in tutte_catene:
        utenti_ordinati = tuple(sorted(catena['utenti']))
        if utenti_ordinati not in combinazioni_viste:
            combinazioni_viste.add(utenti_ordinati)
            catene_uniche.append(catena)

    # Separa scambi diretti e catene lunghe
    scambi_diretti = [c for c in catene_uniche if c.get('tipo') == 'scambio_diretto']
    catene_lunghe = [c for c in catene_uniche if c.get('tipo') != 'scambio_diretto']

    # Ordina per qualità (scambi diretti hanno massima priorità)
    scambi_diretti_alta = [c for c in scambi_diretti if c.get('categoria_qualita') == 'alta']
    scambi_diretti_generici = [c for c in scambi_diretti if c.get('categoria_qualita') == 'generica']

    catene_alta_qualita = [c for c in catene_lunghe if c.get('categoria_qualita') == 'alta']
    catene_generiche = [c for c in catene_lunghe if c.get('categoria_qualita') == 'generica']


    # Ordina per punteggio
    scambi_diretti_alta.sort(key=lambda x: -x.get('punteggio_qualita', 0))
    scambi_diretti_generici.sort(key=lambda x: -x.get('punteggio_qualita', 0))
    catene_alta_qualita.sort(key=lambda x: (len(x.get('utenti', [])), -x.get('punteggio_qualita', 0)))
    catene_generiche.sort(key=lambda x: (len(x.get('utenti', [])), -x.get('punteggio_qualita', 0)))

    # Aggiungi flag per i preferiti se l'utente è autenticato
    if request.user.is_authenticated:
        for catena in scambi_diretti_alta + scambi_diretti_generici + catene_alta_qualita + catene_generiche:
            catena['is_favorita'] = is_catena_preferita(request.user, catena)

    return render(request, 'scambi/catene_scambio.html', {
        'scambi_diretti_alta': scambi_diretti_alta,
        'scambi_diretti_generici': scambi_diretti_generici,
        'catene_alta_qualita': catene_alta_qualita,
        'catene_generiche': catene_generiche,
        'totale_catene': len(catene_uniche),
        'totale_scambi_diretti': len(scambi_diretti),
        'totale_catene_lunghe': len(catene_lunghe),
        'ricerca_eseguita': cerca_nuove,
        'user_filtered': request.user.is_authenticated and cerca_nuove
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
            scambi_diretti = trova_scambi_diretti()
            catene = trova_catene_scambio()

            # Separa catene per qualità (come nella vista originale)
            catene_alta_qualita = [c for c in catene if c.get('categoria_qualita') == 'alta']
            catene_generiche = [c for c in catene if c.get('categoria_qualita') == 'generica']

            # Filtra tutto per l'utente attuale
            scambi_diretti_utente, catene_lunghe_utente = filtra_catene_per_utente(
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

    return render(request, 'scambi/modifica_profilo.html', {
        'form': form,
        'profilo': profilo
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
        scambi_diretti = trova_scambi_diretti()
        catene = trova_catene_scambio()

        # Separa catene per qualità (come nella vista originale)
        catene_alta_qualita = [c for c in catene if c.get('categoria_qualita') == 'alta']
        catene_generiche = [c for c in catene if c.get('categoria_qualita') == 'generica']

        # Filtra tutto per l'utente attuale
        scambi_diretti_utente, catene_lunghe_utente = filtra_catene_per_utente(
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

    if cerca_nuove and ha_annunci:
        # Import delle funzioni di matching
        from .matching import trova_catene_scambio, trova_scambi_diretti, filtra_catene_per_utente

        print(f"🔍 RICERCA LE MIE CATENE per utente: {request.user.username}")

        try:
            start_time = time.time()
            timeout_seconds = 15  # 15 secondi di timeout (ultra-sicuro)

            # Esegui ricerca con limitazioni per evitare timeout
            print("⏰ Inizio ricerca scambi diretti...")
            scambi_diretti = trova_scambi_diretti()

            if time.time() - start_time > timeout_seconds:
                messages.error(request, 'Ricerca interrotta per timeout. Troppi dati da elaborare.')
                tutte_catene = scambi_diretti
            else:
                print("⏰ Inizio ricerca catene lunghe (limitata a 3 utenti)...")
                try:
                    # Limita la ricerca delle catene a max 3 utenti per velocizzare
                    catene = trova_catene_scambio(max_lunghezza=3)

                    if time.time() - start_time > timeout_seconds:
                        messages.warning(request, 'Ricerca parziale completata (timeout raggiunto). Mostrando solo scambi diretti.')
                        tutte_catene = scambi_diretti
                    else:
                        # Separa catene per qualità
                        catene_alta_qualita = [c for c in catene if c.get('categoria_qualita') == 'alta']
                        catene_generiche = [c for c in catene if c.get('categoria_qualita') == 'generica']

                        # Filtra tutto per l'utente attuale
                        scambi_diretti_utente, catene_lunghe_utente = filtra_catene_per_utente(
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

        # Separa scambi diretti e catene lunghe
        scambi_diretti = [c for c in catene_uniche if c.get('tipo') == 'scambio_diretto']
        catene_lunghe = [c for c in catene_uniche if c.get('tipo') != 'scambio_diretto']

        # Ordina per qualità
        scambi_diretti_alta = [c for c in scambi_diretti if c.get('categoria_qualita') == 'alta']
        scambi_diretti_generici = [c for c in scambi_diretti if c.get('categoria_qualita') == 'generica']
        catene_alta_qualita = [c for c in catene_lunghe if c.get('categoria_qualita') == 'alta']
        catene_generiche = [c for c in catene_lunghe if c.get('categoria_qualita') == 'generica']

        # Ordina per punteggio
        scambi_diretti_alta.sort(key=lambda x: -x.get('punteggio_qualita', 0))
        scambi_diretti_generici.sort(key=lambda x: -x.get('punteggio_qualita', 0))
        catene_alta_qualita.sort(key=lambda x: (len(x.get('utenti', [])), -x.get('punteggio_qualita', 0)))
        catene_generiche.sort(key=lambda x: (len(x.get('utenti', [])), -x.get('punteggio_qualita', 0)))

        # Aggiungi flag per i preferiti se l'utente è autenticato
        if request.user.is_authenticated:
            for catena in scambi_diretti_alta + scambi_diretti_generici + catene_alta_qualita + catene_generiche:
                catena['is_favorita'] = is_catena_preferita(request.user, catena)

        # Ottieni le catene preferite dell'utente
        catene_preferite = CatenaPreferita.objects.filter(utente=request.user).order_by('-data_creazione')

        context = {
            'scambi_diretti_alta': scambi_diretti_alta,
            'scambi_diretti_generici': scambi_diretti_generici,
            'catene_alta_qualita': catene_alta_qualita,
            'catene_generiche': catene_generiche,
            'catene_preferite': catene_preferite,
            'totale_catene': len(catene_uniche),
            'totale_scambi_diretti': len(scambi_diretti),
            'totale_catene_lunghe': len(catene_lunghe),
            'ricerca_eseguita': True,
            'personalizzato': True,
        }

    elif cerca_nuove and not ha_annunci:
        # Utente ha cercato ma non ha annunci
        # Ottieni le catene preferite dell'utente
        catene_preferite = CatenaPreferita.objects.filter(utente=request.user).order_by('-data_creazione')

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
        }
        messages.warning(request, 'Non hai annunci attivi! Pubblica un annuncio per trovare opportunità di scambio.')
    else:
        # Prima visita - mostra interfaccia vuota
        # Ottieni le catene preferite dell'utente
        catene_preferite = CatenaPreferita.objects.filter(utente=request.user).order_by('-data_creazione')

        context = {
            'ricerca_eseguita': False,
            'personalizzato': True,
            'ha_annunci': ha_annunci,
            'catene_preferite': catene_preferite,
        }

    return render(request, 'scambi/catene_scambio.html', context)


# === HELPER FUNCTIONS PER CATENE PREFERITE ===
import hashlib
import json

def genera_hash_catena(catena_data):
    """Genera un hash univoco per una catena basato sui partecipanti e annunci"""
    # Crea una rappresentazione stabile della catena
    utenti = sorted(catena_data.get('utenti', []))
    annunci = []
    for item in catena_data.get('annunci_coinvolti', []):
        annunci.append({
            'annuncio_id': item.get('annuncio', {}).get('id') if hasattr(item.get('annuncio'), 'id') else item.get('annuncio'),
            'utente': item.get('utente'),
            'ruolo': item.get('ruolo')
        })
    annunci = sorted(annunci, key=lambda x: (x['annuncio_id'], x['utente']))

    # Crea stringa per hash
    hash_string = f"{'-'.join(utenti)}:{json.dumps(annunci, sort_keys=True)}"
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
        # Recupera i dati della catena dal POST
        catena_data_json = request.POST.get('catena_data')
        if not catena_data_json:
            return JsonResponse({'success': False, 'error': 'Dati catena mancanti'})

        catena_data = json.loads(catena_data_json)
        catena_hash = genera_hash_catena(catena_data)

        # Controlla se la catena è già nei preferiti
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

    except json.JSONDecodeError:
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
    """Context processor per aggiungere dati notifiche a tutti i template"""
    if request.user.is_authenticated:
        return {
            'notifiche_non_lette': conta_notifiche_non_lette(request.user),
            'notifiche_recenti': ottieni_notifiche_recenti(request.user, 5)
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
            annunci = annunci.filter(prezzo_stimato__gte=prezzo_min)

        # Filtro per prezzo massimo
        prezzo_max = form.cleaned_data.get('prezzo_max')
        if prezzo_max:
            ricerca_effettuata = True
            annunci = annunci.filter(prezzo_stimato__lte=prezzo_max)

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
from .notifications import notifica_nuovo_messaggio
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

            # Notifica gli altri utenti nella conversazione
            altri_utenti = conversazione.get_altri_utenti(request.user)
            for utente in altri_utenti:
                notifica_nuovo_messaggio(utente, messaggio)

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

        # Notifica il destinatario
        notifica_nuovo_messaggio(destinatario, messaggio)

        return JsonResponse({
            'success': True,
            'conversazione_id': conversazione.id,
            'messaggio': 'Messaggio inviato con successo!'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Dati JSON non validi'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Errore del server'}, status=500)
