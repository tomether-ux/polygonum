---
description: Colori brand e linee guida di design per Polygonum
when_to_use: Quando lavori su UI, styling o nuovi componenti
---

# Branding Polygonum

## Palette Colori Brand

### Colori Primari
- **Blu Polygonum (Primary)**: `#4169E1` (Royal Blue)
  - Usato per: CTA principali, link, evidenziazioni
  - Hover: `#2E4C9C` (blu più scuro)

- **Bianco**: `#ffffff` / `white`
  - Usato per: sfondi card, container principali

### Colori Testo
- **Grigio Scuro**: `#4A5568`
  - Usato per: titoli, testo principale (es. hero title)

- **Grigio Medio**: `#6c757d`
  - Usato per: testo secondario, slogan, sottotitoli

- **Grigio Chiaro**: `#adb5bd`
  - Usato per: username, dettagli meno importanti

### Colori UI
- **Bordi**: `#e5e7eb`
  - Usato per: navbar borders, separatori

- **Background Chiaro**: `#f8f9fa`
  - Usato per: hover states, placeholder

- **Background Scuro**: `#2c3e50`
  - Usato per: header accordion, elementi di enfasi

### Colori Funzionali
- **Verde Success**: `#28a745`
  - Usato per: prezzi, indicatori positivi

- **Background Texture**: `#f5f7fa` → `#c3cfe2`
  - Gradient: `linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)`

## Linee Guida Design

### Tipografia
- **Titoli Hero**: 2.8rem (mobile: 2.2rem), font-weight: 700
- **Slogan**: 3rem (mobile: 1.8rem)
- **Display Titles**: display-6, uppercase, bold

### Spacing
- **Border Radius**: 16px per card moderne
- **Padding Card**: 40px (mobile: 30px 15px)
- **Gap tra elementi**: 12px-16px

### Effetti
- **Box Shadow Card**: `0 8px 32px rgba(0, 0, 0, 0.1)`
- **Box Shadow Hover**: `0 8px 24px rgba(0, 0, 0, 0.12)`
- **Backdrop Filter**: `blur(10px)` per elementi glassmorphism
- **Transform Hover**: `translateY(-4px)`

### Classi Custom
- `.text-polygonum-primary` - testo blu brand
- `.btn-primary` - bottone blu brand
- `.btn-outline-primary` - bottone outline blu brand
- `.modern-card` - card design moderno con hover effect

## Note di Implementazione
- Usa sempre `transition: all 0.2s ease` per hover states
- Border bottom di 2px per elementi attivi in navbar
- Immagini: `object-fit: cover` per mantenere proporzioni
- Mobile first: media query `@media (max-width: 768px)`
