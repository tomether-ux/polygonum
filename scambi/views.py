from django.shortcuts import render
from django.http import HttpResponse
from .matching import trova_catene_scambio
from .models import Annuncio

def test_matching(request):
    """Vista per testare l'algoritmo di matching"""
    catene_semplici = trova_catene_scambio()
    
    html = "<h1>Catene di Scambio Trovate</h1>"
    
    if not catene_semplici:
        html += "<p>Nessuna catena di scambio semplice trovata.</p>"
        html += "<h2>Annunci Attuali:</h2>"
        
        # Mostra tutti gli annunci per debug
        annunci_offro = Annuncio.objects.filter(tipo='offro', attivo=True)
        annunci_cerco = Annuncio.objects.filter(tipo='cerco', attivo=True)
        
        html += "<h3>Annunci 'Offro':</h3><ul>"
        for annuncio in annunci_offro:
            html += f"<li>{annuncio.utente.username}: {annuncio.titolo}</li>"
        html += "</ul>"
        
        html += "<h3>Annunci 'Cerco':</h3><ul>"
        for annuncio in annunci_cerco:
            html += f"<li>{annuncio.utente.username}: {annuncio.titolo}</li>"
        html += "</ul>"
    else:
        html += f"<p>🎉 Trovate {len(catene_semplici)} catene di scambio semplici!</p>"
        
        for i, catena in enumerate(catene_semplici, 1):
            html += f"<h3>Catena Semplice {i}:</h3>"
            html += f"<p><strong>Partecipanti:</strong> {', '.join(catena['utenti'])}</p>"
            html += "<ul>"
            for scambio in catena['scambi']:
                html += f"<li>{scambio}</li>"
            html += "</ul><hr>"
    
    return HttpResponse(html)
def home(request):
    """Vista principale del sito"""
    return render(request, 'scambi/home.html')

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
        form = AnnuncioForm(request.POST)
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
    tutte_catene = trova_catene_scambio()
    
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
        'totale_catene': len(catene_uniche)
    })

# La funzione test_matching rimane uguale...
