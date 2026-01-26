"""
Tips per la newsletter Polygonum
Lista di consigli utili inviati a rotazione
"""

TIPS = [
    {
        "titolo": "Usa foto di qualità",
        "testo": "Gli annunci con foto chiare e ben illuminate ricevono fino al 3x più visualizzazioni. Scatta in buona luce naturale!"
    },
    {
        "titolo": "Descrizioni dettagliate",
        "testo": "Più dettagli = più fiducia. Includi condizioni, dimensioni, anno di acquisto e motivo dello scambio."
    },
    {
        "titolo": "Indica il valore",
        "testo": "Specificare la fascia di prezzo aiuta a trovare scambi equi più velocemente. È solo indicativo!"
    },
    {
        "titolo": "Crea annunci 'Cerco'",
        "testo": "Non solo 'offro'! Gli annunci 'cerco' aumentano le possibilità di trovare catene di scambio multilaterali."
    },
    {
        "titolo": "Specifica la zona",
        "testo": "Indica chiaramente se preferisci scambi a mano o spedizione. Gli scambi locali sono più veloci!"
    },
    {
        "titolo": "Rispondi velocemente",
        "testo": "Le prime 24 ore sono cruciali. Chi risponde rapidamente completa il doppio degli scambi."
    },
    {
        "titolo": "Esplora le catene",
        "testo": "Le catene di scambio multilaterali aprono possibilità incredibili. Controlla regolarmente la sezione 'Catene'!"
    },
    {
        "titolo": "Mantieni aggiornati gli annunci",
        "testo": "Hai già scambiato? Disattiva l'annuncio per non ricevere proposte inutili e aiutare gli altri utenti."
    },
    {
        "titolo": "Sii specifico nei titoli",
        "testo": "Invece di 'Libro', scrivi 'Harry Potter e la Pietra Filosofale - Prima edizione'. Migliore matching!"
    },
    {
        "titolo": "Comunicazione chiara",
        "testo": "Prima di confermare, allineati su: condizioni dell'oggetto, modalità di scambio e tempistiche. Evita malintesi!"
    }
]

def get_random_tip():
    """Restituisce un tip casuale dalla lista"""
    import random
    return random.choice(TIPS)

def get_tip_by_index(index):
    """Restituisce un tip specifico per indice (rotazione deterministica)"""
    return TIPS[index % len(TIPS)]
