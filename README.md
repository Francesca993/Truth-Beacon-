# Truth Beacon AI 🔍

Sistema avanzato di fact-checking con analisi multi-fonte, scoring di credibilità e verdetto motivato.

👉 Verifica affermazioni in tempo reale usando Google Gemini  
👉 Mostra fake news recenti da fonti di fact-check affidabili  

---

## 🚀 Come funziona

Il progetto è composto da due parti principali:

### 1. Fact-check automatico
- Inserisci un'affermazione (claim)
- Il sistema interroga Google Gemini
- Gemini esegue ricerche web in tempo reale
- Restituisce:
  - Verdettto (VERO / FALSO / PARZIALE / NON VERIFICABILE)
  - Confidence score
  - Fonti utilizzate
  - Analisi dettagliata

👉 L’AI confronta più fonti e segnala eventuali discrepanze, anche temporali.

---

### 2. Archivio fake news (live)
La pagina `fakenews.html` mostra smentite aggiornate da feed di fact-check:

- PolitiFact
- Snopes
- FactCheck.org
- Full Fact
- Facta
- Pagella Politica

Il sistema:
- raccoglie articoli RSS
- filtra contenuti rilevanti (debunk, bufale, misinformation)
- classifica il tipo di fake news (deepfake, dati falsi, contenuti riciclati, ecc.)

---

## ⚙️ Setup in 3 passi

### 1. Ottieni la chiave API gratuita

https://aistudio.google.com/apikey

1. Accedi con il tuo account Google  
2. Clicca "Create API key"  
3. Copia la chiave (inizia con `AIzaSy...`)  

---

### 2. Installa le dipendenze

```bash
pip install -r requirements.txt
```

### 3. Avvia il server locale

```
python server.py
```

Apri:
👉 http://localhost:8080
Incolla la tua API key nel campo in cima alla pagina e sei pronto.

### 🧱 Struttura del progetto

factcheck/
├── index.html          # Interfaccia fact-check
├── fakenews.html       # Archivio fake news
├── server.py           # Server locale + API
├── rss_collector.py    # Raccolta e filtro RSS
├── requirements.txt    # Dipendenze
└── README.md


### 🧠 Logica di fact-check
Il sistema utilizza:
- Analisi multi-fonte
- Confronto tra fonti recenti e storiche
- Identificazione discrepanze tra versioni diverse della stessa notizia
- Scoring di credibilità delle fonti

Classificazione risultati:
* ✔️ VERO
* ❌ FALSO
* ⚠️ PARZIALMENTE VERO
* ❓ NON VERIFICABILE
---

📊 Fonti e credibilità
| Fonte            | Score |
| ---------------- | ----- |
| BBC News         | 95    |
| Reuters          | 95    |
| Le Monde         | 90    |
| Associated Press | 93    |
| The Guardian     | 88    |
| Il Sole 24 Ore   | 85    |
| ...              | ...   |

## 🏆 Hackathon

Progetto sviluppato per la challenge **“Truth Engine: combattere la disinformazione”** durante l’hackathon di {Codemotion}

Obiettivo della challenge:
costruire un sistema AI capace di verificare informazioni in tempo reale, analizzando fonti multiple e fornendo un fact-check chiaro e affidabile.

---

## 👥 Team

**Team 42 Desaparesidos**

- Francesca Montini  
- Federico Pennarola  

---

## 🎯 Obiettivo del progetto

Sviluppare un sistema di fact-checking che:
- analizza automaticamente più fonti
- confronta informazioni nel tempo
- identifica discrepanze e contenuti riciclati
- restituisce un verdetto chiaro e motivato

---

## 💡 Approccio

Il progetto si distingue per:
- uso di AI per ricerca e analisi in tempo reale
- confronto tra fonti recenti e storiche
- attenzione alle incoerenze tra versioni della stessa notizia