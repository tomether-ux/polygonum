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

    # Separa per qualità
    catene_alta_qualita = [c for c in catene_uniche if c.get('categoria_qualita') == 'alta']
    catene_generiche = [c for c in catene_uniche if c.get('categoria_qualita') == 'generica']

    catene_alta_qualita.sort(key=lambda x: (len(x.get('utenti', [])), -x.get('punteggio_qualita', 0)))
    catene_generiche.sort(key=lambda x: (len(x.get('utenti', [])), -x.get('punteggio_qualita', 0)))

    return render(request, 'scambi/catene_scambio.html', {
        'catene_alta_qualita': catene_alta_qualita,
        'catene_generiche': catene_generiche,
        'totale_catene': len(catene_uniche),
        'ricerca_eseguita': cerca_nuove
    })

# La funzione test_matching rimane uguale...
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from .forms import CustomUserCreationForm

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registrazione completata!')
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
