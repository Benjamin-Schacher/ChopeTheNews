import argparse
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path

from veille import collecte, dashboard, rapport, stockage
from veille.config import charger_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Veille de news")
    parser.add_argument("-c", "--config", type=Path, default=Path("config.yaml"), help="fichier de config")
    parser.add_argument("-j", "--jours", type=int, help="remplace periode_jours de la config")
    parser.add_argument("--sans-collecte", action="store_true", help="régénère les rapports depuis la base, sans rien télécharger")
    parser.add_argument("--no-open", action="store_true", help="n'ouvre pas le dashboard dans le navigateur")
    args = parser.parse_args()

    config = charger_config(args.config)
    if args.jours:
        config.periode_jours = args.jours

    db = stockage.ouvrir(config.base_de_donnees)
    if not args.sans_collecte:
        print(f"Collecte sur {config.periode_jours} jour(s)...")
        articles = collecte.collecter(config)
        nouveaux = stockage.enregistrer(db, articles)
        print(f"{len(articles)} article(s) trouvé(s), dont {nouveaux} nouveau(x).")

    depuis = datetime.now(timezone.utc) - timedelta(days=config.periode_jours)
    selection = stockage.articles_depuis(db, depuis)
    chemin_md = rapport.generer(selection, config.dossier_rapports, config.periode_jours)
    chemin_html = dashboard.generer(selection, config.dossier_rapports, config.periode_jours)
    print(f"Rapport : {chemin_md}")
    print(f"Dashboard : {chemin_html}")

    if config.ouvrir_navigateur and not args.no_open:
        webbrowser.open(chemin_html.resolve().as_uri())
