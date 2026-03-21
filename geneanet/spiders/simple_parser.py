"""
Firefox Parser : Logique de parsing et de traitement des pages.

Héritage :
- FirefoxCrawler (pour le crawling et le cache).

Fonctionnalités :
- Recherche d'un texte cible dans les pages.
- Extraction des liens si le texte est trouvé.
- Ajout des liens à la file uniquement s'ils contiennent "lang=fr".
- Gestion de la profondeur via les métadonnées.
"""

from crawler import FirefoxCrawler
from bs4 import BeautifulSoup
import logging
import sys

class FirefoxParser(FirefoxCrawler):
    def __init__(self, target_text="bonjour", max_pages=50):
        super().__init__(max_pages)
        self.target_text = target_text

    def parse_page(self, url, html_content, meta):
        """Parse une page : recherche le texte cible et extrait les liens si trouvé.
        Args:
            meta (dict): Contient la profondeur actuelle.
        """
        if self.target_text.lower() in html_content.lower():
            logging.info(f'Texte "{self.target_text}" trouvé sur {url} (profondeur: {meta.get("profondeur", 1)})')
            # Extrait les liens uniquement si le texte est trouvé
            soup = BeautifulSoup(html_content, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.startswith(("http://", "https://")):
                    if "&lang=fr" in href and "&n=" in href:
                        new_meta = meta.copy()
                        new_meta["profondeur"] = meta.get("profondeur", 1) + 1
                        self.add_link(href, new_meta)
                elif href.startswith("/"):
                    from urllib.parse import urljoin
                    full_url = urljoin(url, href)
                    if "&lang=fr" in full_url and "&n=" in full_url:
                        new_meta = meta.copy()
                        new_meta["profondeur"] = meta.get("profondeur", 1) + 1
                        self.add_link(full_url, new_meta)
        else:
            logging.info(f'Texte "{self.target_text}" non trouvé sur {url} (profondeur: {meta.get("profondeur", 1)})')

    def start(self, start_url):
        """Démarre le crawl avec l'URL de départ et métadonnées initiales."""
        self.crawl(start_url, meta={"profondeur": 1})
        self.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python main.py <URL_DE_DEPART>")
        sys.exit(1)
    crawler = FirefoxParser(target_text="dupont", max_pages=10)
    crawler.start(sys.argv[1])