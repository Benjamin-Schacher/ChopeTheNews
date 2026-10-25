import calendar
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, quote_plus, urlparse

import feedparser
import httpx
import trafilatura

from veille.config import Config

USER_AGENT = "Mozilla/5.0 (compatible; veille-news/0.1)"
PAGES_BING = 4
RE_IMG =re.compile(r"""<img[^>]+src=["']([^"']+)""", re.IGNORECASE)


@dataclass
class Article:
    theme: str
    source: str
    titre: str
    url: str
    date: datetime | None
    resume: str
    image: str | None = None
    site: str | None = None


def url_google_news(requete: str, jours: int, langue: str, pays: str) -> str:
    q = quote_plus(f"{requete} when:{jours}d")
    return f"https://news.google.com/rss/search?q={q}&hl={langue}&gl={pays}&ceid={pays}:{langue}"


def url_bing_news(requete: str, langue: str, pays: str, premier: int) -> str:
    q = quote_plus(requete)
    tri = quote_plus('sortbydate="1"')
    return f"https://www.bing.com/news/search?q={q}&format=rss&setlang={langue}&cc={pays}&first={premier}&qft={tri}"


def est_google_news(url: str) -> bool:
    return urlparse(url).netloc == "news.google.com"


def _lien_bing(lien: str) -> str:
    """Les liens Bing News passent par apiclick.aspx?url=<vrai lien>."""
    if urlparse(lien).netloc.endswith("bing.com"):
        if vrai := parse_qs(urlparse(lien).query).get("url"):
            return vrai[0]
    return lien


def _domaine(url: str | None) -> str | None:
    if not url:
        return None
    return urlparse(url).netloc.removeprefix("www.") or None


def _date_entree(entree) -> datetime | None:
    t = entree.get("published_parsed") or entree.get("updated_parsed")
    if not t:
        return None
    return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)


def _image_entree(entree) -> str | None:
    """Cherche une image dans les balises média du flux, puis dans le HTML du résumé."""
    if bing := entree.get("news_image"):
        # Miniature Bing : on demande une taille adaptée aux cartes du dashboard
        return bing.replace("http://", "https://", 1) + "&w=640&h=360&c=7"
    for media in entree.get("media_thumbnail", []) + entree.get("media_content", []):
        if media.get("url") and media.get("medium", "image") == "image":
            return media["url"]
    for lien in entree.get("enclosures", []) + entree.get("links", []):
        if lien.get("type", "").startswith("image/") and lien.get("href"):
            return lien["href"]
    contenus = [c.get("value", "") for c in entree.get("content", [])] + [entree.get("summary", "")]
    for html in contenus:
        if m := RE_IMG.search(html):
            return m.group(1)
    return None


def _sans_accents(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texte.lower()) if not unicodedata.combining(c))


def _termes(requete: str) -> tuple[list[str], list[str]]:
    """Découpe une requête en termes recherchés et termes exclus (-mot), sans les opérateurs."""
    inclus, exclus = [], []
    for signe, phrase, mot in re.findall(r'(-?)(?:"([^"]+)"|(\S+))', requete):
        terme = phrase or mot
        if not phrase and (terme == "OR" or terme.startswith("site:")):
            continue
        terme = _sans_accents(terme.removeprefix("intitle:"))
        (exclus if signe else inclus).append(terme)
    return inclus, exclus


def _pertinent(article: "Article", requete: str) -> bool:
    """Bing renvoie parfois l'actu générale du moment : on vérifie que l'article parle bien de la requête."""
    texte = _sans_accents(f"{article.titre} {article.resume}")
    contient = lambda t: re.search(rf"\b{re.escape(t)}\b", texte) is not None
    inclus, exclus = _termes(requete)
    return any(map(contient, inclus)) and not any(map(contient, exclus))


def _nettoyer(html: str) -> str:
    texte = trafilatura.extract(f"<html><body><p>{html}</p></body></html>") if html else None
    return (texte or "").strip()


def lire_flux(
    client: httpx.Client, url: str, theme: str, source: str, depuis: datetime, requete: str | None = None
) -> list[Article]:
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
        source_entree = entree.get("source", {}).get("title") or entree.get("news_source") or nom_source
        titre = entree.get("title", "(sans titre)").strip()
        resume = _nettoyer(entree.get("summary", ""))
        # Google News : titre suffixé par " - Source", résumé qui ne fait que répéter le titre
        titre = titre.removesuffix(f" - {source_entree}")
        if resume.startswith(titre):
            resume = ""
        lien = _lien_bing(entree.get("link", ""))
        article = Article(
            theme=theme,
            source=source_entree,
            titre=titre,
            url=lien,
            date=date,
            resume=resume,
            image=_image_entree(entree),
            site=_domaine(entree.get("source", {}).get("href") or lien),
        )
        if requete is None or _pertinent(article, requete):
            articles.append(article)
    print(f"  {source if source != url else nom_source} : {len(articles)} article(s)")
    return articles


def enrichir(client: httpx.Client, article: Article, texte_complet: bool) -> None:
    """Télécharge la page de l'article pour son image (og:image) et, si demandé, son texte complet."""
    try:
        html = client.get(article.url).text
    except httpx.HTTPError:
        return
    if not article.image:
        meta = trafilatura.extract_metadata(html)
        if meta and meta.image:
            article.image = meta.image
    if texte_complet and (texte := trafilatura.extract(html)):
        article.resume = texte


def collecter(config: Config) -> list[Article]:
    depuis = datetime.now(timezone.utc) - timedelta(days=config.periode_jours)
    gn = config.google_news

    taches = []
    for nom, theme in config.themes.items():
        for site in theme.sites:
            taches.append((site, nom, site, None))
        for requete in theme.recherches:
            if "google_news" in config.moteurs:
                url = url_google_news(requete, config.periode_jours, gn.langue, gn.pays)
                taches.append((url, nom, f"Google News « {requete} »", None))
            if "bing_news" in config.moteurs:
                # Bing renvoie ~12 résultats par page : on en lit plusieurs, filtrés par pertinence
                for page in range(PAGES_BING):
                    url = url_bing_news(requete, gn.langue, gn.pays, 1 + page * 12)
                    taches.append((url, nom, f"Bing News « {requete} » p.{page + 1}", requete))

    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=True) as client:
        with ThreadPoolExecutor(max_workers=8) as pool:
            resultats = pool.map(lambda t: lire_flux(client, t[0], t[1], t[2], depuis, t[3]), taches)
            articles = [a for lot in resultats for a in lot]

        # Les liens Google News sont des redirections JavaScript : inutile d'aller chercher la page
        a_enrichir = [
            a for a in articles
            if not est_google_news(a.url) and (config.extraire_contenu or (config.recuperer_images and not a.image))
        ]
        if a_enrichir:
            print(f"Récupération des pages de {len(a_enrichir)} article(s)...")
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda a: enrichir(client, a, config.extraire_contenu), a_enrichir))

    return articles
