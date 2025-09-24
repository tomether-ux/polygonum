from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import UserCreationForm  # Se usi il form base
from django.shortcuts import render
from django.http import HttpResponse
from .matching import trova_catene_scambio
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
def i_miei_annunci(request):
    """Mostra gli annunci dell'utente corrente"""
    annunci = Annuncio.objects.filter(utente=request.user).order_by('-data_creazione')
    
    return render(request, 'scambi/i_miei_annunci.html', {'annunci': annunci})

def catene_scambio(request):
    """Mostra le catene di scambio divise per qualità"""
    # Controlla se è stata richiesta una nuova ricerca
    cerca_nuove = request.GET.get('cerca') == 'true'

    if cerca_nuove:
        # Ricarica il modulo matching per applicare eventuali modifiche
        importlib.reload(matching)
        from .matching import trova_catene_scambio

        print("🔍 RICERCA CATENE ATTIVATA MANUALMENTE")
        tutte_catene = trova_catene_scambio()
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

    return render(request, 'scambi/catene_scambio.html', {
        'scambi_diretti_alta': scambi_diretti_alta,
        'scambi_diretti_generici': scambi_diretti_generici,
        'catene_alta_qualita': catene_alta_qualita,
        'catene_generiche': catene_generiche,
        'totale_catene': len(catene_uniche),
        'totale_scambi_diretti': len(scambi_diretti),
        'totale_catene_lunghe': len(catene_lunghe),
        'ricerca_eseguita': cerca_nuove
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

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Invia email di verifica
            user_profile = UserProfile.objects.get(user=user)
            if send_verification_email(request, user, user_profile):
                messages.success(request,
                    f'Registrazione completata! Ti abbiamo inviato un\'email di verifica a {user.email}. '
                    'Controlla la tua casella di posta e clicca sul link per attivare il tuo account.')
            else:
                messages.warning(request,
                    'Registrazione completata ma c\'è stato un problema nell\'invio dell\'email di verifica. '
                    'Controlla i log del server o contatta il supporto.')

            return redirect('login')
        else:
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

    # Ottieni tutti gli annunci dell'utente (attivi)
    annunci = Annuncio.objects.filter(utente=utente, attivo=True).order_by('-data_creazione')

    # Dividi annunci per tipo
    annunci_offro = annunci.filter(tipo='offro')
    annunci_cerco = annunci.filter(tipo='cerco')

    return render(request, 'scambi/profilo_utente.html', {
        'utente': utente,
        'profilo': profilo,
        'annunci_offro': annunci_offro,
        'annunci_cerco': annunci_cerco,
        'totale_annunci': annunci.count(),
        'is_own_profile': request.user == utente
    })

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
