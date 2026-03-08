# 🗺️ Struttura Sito Polygonum

Mappa completa di tutte le pagine e funzionalità del sito.

---

## 📱 PAGINE PRINCIPALI

### Home
- `/` - Homepage

---

## 📢 ANNUNCI

### Visualizzazione
- `/annunci/` - Lista tutti gli annunci
- `/annuncio/<id>/` - Dettaglio singolo annuncio
- `/cerca/` - Ricerca avanzata annunci
- `/ricerca-veloce/` - Ricerca veloce (AJAX)

### Gestione (Autenticato)
- `/crea-annuncio/` - Crea nuovo annuncio
- `/modifica-annuncio/<id>/` - Modifica annuncio
- `/elimina-annuncio/<id>/` - Elimina annuncio
- `/attiva-annuncio/<id>/` - Attiva annuncio
- `/disattiva-annuncio/<id>/` - Disattiva annuncio

---

## 🔗 CATENE DI SCAMBIO

### Visualizzazione
- `/catene-scambio/` - Esplora catene di scambio
- `/catene-attivabili/` - Lista catene attivabili
- `/catena/<id>/` - Dettaglio catena specifica
- `/le-mie-catene/` - Le mie catene personali

### Azioni
- `/catena/<id>/attiva/` - Attiva catena
- `/catene/proponi/<ciclo_id>/` - Proponi catena
- `/catene/rispondi/<proposta_id>/` - Rispondi a proposta catena
- `/catene/stato/<ciclo_id>/` - Stato proposta catena
- `/mie-proposte-catene/` - Mie proposte catene
- `/catene/aggiungi-preferita/` - Aggiungi catena ai preferiti

---

## 💬 MESSAGGISTICA

- `/messaggi/` - Lista conversazioni
- `/messaggi/<conversazione_id>/` - Chat conversazione
- `/messaggi/verifica-conversazione/<user_id>/` - Verifica conversazione esistente
- `/messaggi/invia-da-annuncio/` - Invia messaggio da annuncio
- `/inizia-conversazione/<username>/` - Inizia nuova conversazione

---

## 🤝 PROPOSTE DI SCAMBIO

- `/proposte-scambio/` - Lista proposte
- `/proposte-scambio/<id>/` - Dettaglio proposta
- `/proposte-scambio/crea/<offerto_id>/<richiesto_id>/` - Crea proposta
- `/proposte-scambio/<id>/rispondi/` - Rispondi a proposta

---

## 👤 AUTENTICAZIONE & PROFILO

### Autenticazione
- `/register/` - Registrazione
- `/login/` - Login
- `/logout/` - Logout
- `/verify-email/<token>/` - Verifica email

### Password Reset
- `/password-reset/` - Richiedi reset password
- `/password-reset/done/` - Conferma invio email
- `/password-reset-confirm/<uidb64>/<token>/` - Conferma reset
- `/password-reset-complete/` - Reset completato

### Profilo
- `/profilo/<username>/` - Visualizza profilo utente
- `/modifica-profilo/` - Modifica il proprio profilo

---

## ⭐ PREFERITI & NOTIFICHE

### Preferiti
- `/preferiti/` - Lista preferiti
- `/preferiti/aggiungi/<annuncio_id>/` - Aggiungi annuncio ai preferiti

### Notifiche
- `/notifiche/` - Lista notifiche
- `/notifiche/<id>/letta/` - Segna notifica come letta
- `/notifiche/<id>/click/` - Redirect da notifica
- `/notifiche/tutte-lette/` - Segna tutte come lette

---

## 💎 PREMIUM

- `/pricing/` - Piani e prezzi
- `/premium/checkout/` - Checkout pagamento
- `/premium/success/` - Pagamento completato
- `/premium/cancel/` - Pagamento annullato

---

## 📧 NEWSLETTER

- `/newsletter/unsubscribe/<token>/` - Disiscrizione newsletter

---

## 📖 INFORMAZIONI & GUIDE

### Guide
- `/come-funziona/` - Come funziona Polygonum
- `/guida/catene-scambio/` - Guida catene di scambio
- `/guida/annunci/` - Guida annunci
- `/guida/scambi-sicuri/` - Consigli scambi sicuri

### Community
- `/regolamento/` - Regolamento community
- `/sistema-moderazione/` - Sistema di moderazione

### Informazioni
- `/chi-siamo/` - Chi siamo
- `/contatti/` - Contatti
- `/faq/` - Domande frequenti

---

## ⚖️ PAGINE LEGALI

- `/termini-condizioni/` - Termini e Condizioni
- `/privacy/` - Privacy Policy
- `/cookie/` - Cookie Policy
- `/note-legali/` - Note Legali

---

## 🔧 API & WEBHOOK (Backend)

### API
- `/api/cicli/<user_id>/` - API cicli utente
- `/api/cicli/stats/` - API statistiche cicli

### Webhook
- `/webhook/calcola-cicli/` - Webhook calcolo cicli
- `/webhook/cloudinary-moderation/` - Webhook moderazione Cloudinary

### Moderazione
- `/moderazione/approve/<token>/` - Approva contenuto
- `/moderazione/reject/<token>/` - Rifiuta contenuto

---

## 🐛 DEBUG (Da rimuovere in produzione)

- `/debug/basso/` - Debug basso
- `/debug/view-catene/` - Debug visualizza catene
- `/debug/cyclefinder-basso/` - Debug cyclefinder

---

## 📊 STATISTICHE TOTALI

**Pagine pubbliche:** ~15
**Pagine autenticate:** ~35
**API/Webhook:** ~5
**Pagine legali:** ~4
**Guide:** ~6

**TOTALE ENDPOINTS:** ~134
