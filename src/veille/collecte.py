import calendar
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import feedparser
import httpx
import trafilatura

from veille.config import Config

USER_AGENT = "Mozilla/5.0 (compatible; veille-news/0.1)"


@dataclass
class Article:
    theme: str
    source: str
    titre: str
    url: str
    date: datetime | None
    resume: str


def url_google_news(requete: str, jours: int, langue: str, pays: str) -> str:
    q = quote_plus(f"{requete} when:{jours}d")
    return f"https://news.google.com/rss/search?q={q}&hl={langue}&gl={pays}&ceid={pays}:{langue}"


def _date_entree(entree) -> datetime | None:
    t = entree.get("published_parsed") or entree.get("updated_parsed")
    if not t:
        return None
    return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)


def _nettoyer(html: str) -> str:
    texte = trafilatura.extract(f"<html><body><p>{html}</p></body></html>") if html else None
    return (texte or "").strip()


def lire_flux(client: httpx.Client, url: str, theme: str, source: str, depuis: datetime) -> list[Article]:
    try:
        reponse = client.get(url)
        reponse.raise_for_status()
    except httpx.HTTPError as e:
        print(f"  [erreur] {source} : {e}")
        return []

    flux = feedparser.parse(reponse.content)
    nom_source = flux.feed.get("title", source)
    articles = []
    for entree in flux.entries:
        date = _date_entree(entree)
        if date and date < depuis:
            continue
        source_entree = entree.get("source", {}).get("title") or nom_source
        titre = entree.get("title", "(sans titre)").strip()
        resume = _nettoyer(entree.get("summary", ""))
        # Google News : titre suffixé par " - Source", résumé qui ne fait que répéter le titre
        titre = titre.removesuffix(f" - {source_entree}")
        if resume.startswith(titre):
            resume = ""
        articles.append(
            Article(
                theme=theme,
                source=source_entree,
                titre=titre,
                url=entree.get("link", ""),
                date=date,
                resume=resume,
            )
        )
    print(f"  {nom_source} : {len(articles)} article(s)")
    return articles


def extraire_contenu(client: httpx.Client, article: Article) -> None:
    try:
        reponse = client.get(article.url)
        texte = trafilatura.extract(reponse.text)
    except httpx.HTTPError:
        return
    if texte:
        article.resume = texte


def collecter(config: Config) -> list[Article]:
    depuis = datetime.now(timezone.utc) - timedelta(days=config.periode_jours)
    gn = config.google_news

    taches = []
    for nom, theme in config.themes.items():
        for site in theme.sites:
            taches.append((site, nom, site))
        for requete in theme.recherches:
            url = url_google_news(requete, config.periode_jours, gn.langue, gn.pays)
            taches.append((url, nom, f"Google News « {requete} »"))

    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=True) as client:
        with ThreadPoolExecutor(max_workers=8) as pool:
            resultats = pool.map(lambda t: lire_flux(client, t[0], t[1], t[2], depuis), taches)
            articles = [a for lot in resultats for a in lot]

        if config.extraire_contenu:
            print(f"Extraction du contenu de {len(articles)} article(s)...")
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda a: extraire_contenu(client, a), articles))

    return articles
