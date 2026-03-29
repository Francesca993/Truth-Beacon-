#!/usr/bin/env python3
"""
rss_collector.py — raccolta articoli da feed RSS.
Supporta:
1) modalità legacy "query based" (collect_articles)
2) modalità mirata fact-check (collect_latest_factchecks), usata dalla pagina fakenews
"""

import calendar
import re
import feedparser

FEEDS = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "http://rss.cnn.com/rss/edition.rss",
    "http://feeds.reuters.com/Reuters/worldNews",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://rss.dw.com/rdf/rss-en-all",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://feeds.washingtonpost.com/rss/world",
    "https://www.france24.com/en/rss",
    "https://feeds.npr.org/1004/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://www.repubblica.it/rss/homepage/rss2.0.xml",
    "https://xml.corriereobjects.it/rss/homepage.xml",
    "https://rss.ilsole24ore.com/rss/home.xml",
    "https://www.ansa.it/sito/ansait_rss.xml",
    "https://elpais.com/rss/feed.html",
    "https://www.lemonde.fr/rss/en_continu.xml",
]

FACTCHECK_FEEDS = [
    "https://www.politifact.com/rss/factchecks/",
    "https://www.factcheck.org/feed/",
    "https://www.snopes.com/feed/",
    "https://fullfact.org/feed/",
    "https://www.leadstories.com/hoax-alert/rss.xml",
    "https://facta.news/feed/",
    "https://pagellapolitica.it/feed/",
]

SOURCE_CREDIBILITY = {
    "bbci.co.uk":         ("BBC News", 95),
    "cnn.com":            ("CNN", 75),
    "reuters.com":        ("Reuters", 95),
    "aljazeera.com":      ("Al Jazeera", 78),
    "dw.com":             ("Deutsche Welle", 88),
    "nytimes.com":        ("New York Times", 87),
    "washingtonpost.com": ("Washington Post", 86),
    "france24.com":       ("France 24", 85),
    "npr.org":            ("NPR", 88),
    "theguardian.com":    ("The Guardian", 88),
    "repubblica.it":      ("La Repubblica", 81),
    "corriere.it":        ("Corriere della Sera", 83),
    "ilsole24ore.com":    ("Il Sole 24 Ore", 85),
    "ansa.it":            ("ANSA", 82),
    "elpais.com":         ("El País", 87),
    "lemonde.fr":         ("Le Monde", 90),
    "politifact.com":     ("PolitiFact", 92),
    "factcheck.org":      ("FactCheck.org", 92),
    "snopes.com":         ("Snopes", 90),
    "fullfact.org":       ("Full Fact", 90),
    "leadstories.com":    ("Lead Stories", 88),
    "facta.news":         ("Facta.news", 88),
    "pagellapolitica.it": ("Pagella Politica", 89),
}

FACTCHECK_KEYWORDS = (
    "fact check", "fact-check", "debunk", "debunked", "hoax", "false", "misleading",
    "misinformation", "disinformation", "fake", "pant on fire", "pants on fire",
    "bufala", "smentit", "verifica", "falso",
)

def get_source_name(url):
    for domain, (name, score) in SOURCE_CREDIBILITY.items():
        if domain in url:
            return name, score
    return url, 70


def _clean_html(value):
    return re.sub(r"<[^>]+>", "", value or "").strip()


def _entry_timestamp(entry):
    published = entry.get("published_parsed")
    updated = entry.get("updated_parsed")
    parsed = published or updated
    if not parsed:
        return 0
    try:
        return int(calendar.timegm(parsed))
    except Exception:
        return 0


def _looks_like_factcheck(title, summary, description, link):
    blob = f"{title} {summary} {description} {link}".lower()
    return any(term in blob for term in FACTCHECK_KEYWORDS)


def collect_latest_factchecks(max_per_feed=25, max_results=30):
    """
    Raccoglie le ultime notizie da feed specifici di fact-check/debunk.
    Ritorna lista di dict ordinata dal più recente.
    """
    print("\n[RSS] Raccolta fact-check mirata in corso...")
    rows = []
    seen = set()

    for url in FACTCHECK_FEEDS:
        try:
            feed = feedparser.parse(url)
            entries = feed.entries or []
            source_name, cred_score = get_source_name(url)

            for entry in entries[:max_per_feed]:
                title = (entry.get("title") or "").strip()
                summary = _clean_html(entry.get("summary", ""))
                description = _clean_html(entry.get("description", ""))
                link = (entry.get("link") or "").strip()
                pub = entry.get("published", entry.get("updated", ""))

                if not title and not summary:
                    continue

                # Su feed dedicati al fact-check il filtro è permissivo,
                # ma evita articoli totalmente off-topic.
                if not _looks_like_factcheck(title, summary, description, link):
                    continue

                key = (link or title.lower()).strip()
                if not key or key in seen:
                    continue
                seen.add(key)

                rows.append({
                    "title": title,
                    "summary": summary[:300],
                    "link": link,
                    "published": pub,
                    "source": source_name,
                    "credibility": cred_score,
                    "url": url,
                    "_ts": _entry_timestamp(entry),
                })
        except Exception as e:
            print(f"[RSS] Errore feed {url}: {e}")

    rows.sort(key=lambda r: r.get("_ts", 0), reverse=True)
    rows = rows[:max_results]
    for row in rows:
        row.pop("_ts", None)
    print(f"[RSS] Fact-check trovati: {len(rows)}\n")
    return rows


def get_synonyms(word):
    # Lazy import: non rallenta la modalità fact-check.
    try:
        import nltk
        from nltk.corpus import wordnet
    except Exception:
        return []

    try:
        wordnet.synsets('test')
    except LookupError:
        # Niente download automatico: se mancano risorse, fallback rapido.
        return []

    synonyms = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().replace("_", " "))
    return list(synonyms)

def collect_articles(keyword, max_per_feed=15, max_results=20):
    """
    Legacy query mode: raccoglie articoli da feed generalisti filtrando per keyword.
    """
    print(f"\n[RSS] Ricerca: '{keyword}'")

    # Traduzione keyword opzionale (lazy import)
    languages = ["en", "fr", "es", "de", "it"]
    translations = {}
    translator = None
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator
    except Exception:
        translator = None

    for lang in languages:
        if translator is None:
            translations[lang] = keyword
            continue
        try:
            translations[lang] = translator(source='auto', target=lang).translate(keyword)
        except Exception:
            translations[lang] = keyword

    # Sinonimi inglesi
    english_synonyms = []
    for word in translations.get("en", "").split()[:6]:
        english_synonyms += get_synonyms(word)
    english_synonyms = list(set(english_synonyms))

    keywords_it = [keyword.lower()]
    keywords_orig = list(set([t.lower() for t in translations.values()] + english_synonyms))

    print(f"[RSS] Keywords: {keywords_orig[:6]}...")

    results = []
    for url in FEEDS:
        if len(results) >= max_results:
            break
        try:
            feed = feedparser.parse(url)
            entries = feed.entries or []
            source_name, cred_score = get_source_name(url)

            for entry in entries[:max_per_feed]:
                if len(results) >= max_results:
                    break

                title = entry.get("title", "")
                summary = entry.get("summary", "")
                description = entry.get("description", "")
                link = entry.get("link", "")
                pub = entry.get("published", entry.get("updated", ""))

                # Pulizia HTML
                summary = _clean_html(summary)
                description = _clean_html(description)
                combined_orig = (title + " " + summary + " " + description).lower()

                match_it = any(kw in combined_orig for kw in keywords_it)
                match_orig = any(kw in combined_orig for kw in keywords_orig)

                if match_it or match_orig:
                    results.append({
                        "title": title,
                        "summary": summary[:300],
                        "link": link,
                        "published": pub,
                        "source": source_name,
                        "credibility": cred_score,
                        "url": url,
                    })

        except Exception as e:
            print(f"[RSS] Errore feed {url}: {e}")

    print(f"[RSS] Trovati {len(results)} articoli\n")
    return results


def format_for_display(articles):
    """Formatta gli articoli per stampa a terminale."""
    if not articles:
        print("Nessun articolo trovato.")
        return

    for i, art in enumerate(articles, 1):
        print(f"\n{i}. [{art['source']} — credibilità: {art['credibility']}/100]")
        print(f"   {art['title']}")
        print(f"   {art['published']}")
        print(f"   {art['link']}")
        if art['summary']:
            print(f"   {art['summary'][:200]}...")


if __name__ == "__main__":
    kw = input("Inserisci una parola/frase: ").strip().lower()
    if kw in {"factcheck", "fact-check", "fake news", "bufale"}:
        articles = collect_latest_factchecks()
    else:
        articles = collect_articles(kw)
    format_for_display(articles)
