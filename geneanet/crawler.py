"""
FirefoxCrawler - Version Avancée et Complète
=============================================

Un crawler robuste pour Firefox avec :
- Masquage complet de l'environnement d'exécution (anti-détection)
- Comportement humain réaliste (mouvements de souris, clics, scrolls aléatoires)
- Gestion avancée des cookies et sessions
- Contournement des challenges Cloudflare
- Support des proxies rotatifs
- Logs détaillés et statistiques complètes
- Chemin fixe pour geckodriver : C:\\Programs\\GeckoDriver\\geckodriver.exe

Dépendances :
- selenium (pip install selenium)
- fake-useragent (pip install fake-useragent)
"""

import os
import json
import random
import time
import math
import logging
from queue import Queue
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import WebDriverException

# Configuration des logs
#logging.basicConfig(
#    level=logging.INFO,
#    format='%(asctime)s - %(levelname)s - %(message)s',
#    handlers=[
#        #logging.FileHandler("firefox_crawler.log"),
#        logging.StreamHandler()
#    ]
#)
formatter = logging.Formatter(
    #fmt="%(asctime)s %(filename)s:%(lineno)d - %(levelname)s - %(message)s",
    fmt="%(asctime)s %(name)-14s[%(lineno)4d] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"  # supprime les millisecondes
)
# Handler stdout
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.propagate = False  # ← ne remonte pas au root logger
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)

# Chemin fixe pour geckodriver
GECKODRIVER_PATH = "C:\\Programs\\GeckoDriver\\geckodriver.exe"

class FirefoxCrawler:
    def get_logger(self):
        return logger
    def get_formatter():
        return formatter

    """
    Crawler avancé pour Firefox avec contournement des protections anti-bot.

    Args:
        max_pages (int): Nombre maximum de pages à crawler. Default: 50.
        min_delay (float): Délai minimum entre les requêtes (secondes). Default: 0.5.
        max_delay (float): Délai maximum entre les requêtes (secondes). Default: 2.0.
        proxy_list (list): Liste de proxies au format "ip:port". Default: None.
        headless (bool): Activer le mode headless. Default: False.
    """

    def __init__(self, max_pages=50, max_cloudflare_errors=10, min_delay=0.5, max_delay=2.0, headless=False, proxy_list=None):
        self.visited_urls = set()
        self.queue = Queue()
        self.max_pages = max_pages
        self.max_cloudflare_errors = max_cloudflare_errors
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.proxy_list = proxy_list or []
        self.current_proxy_index = 0
        self.headless = headless
        self.cache_dir = "result/pages"
        self.nb_scanned_pages = 0
        self.nb_cached_pages = 0
        self.nb_cloudflare_errors = 0
        self.nb_crawling_errors = 0
        self.nb_cookies_click = 0
        self.abort_crawling = False
        os.makedirs(self.cache_dir, exist_ok=True)

        # Initialisation du driver avec options avancées
        self._init_driver()

        # Masquage des propriétés d'automatisation
        self._hide_automation()
        logger.info("FirefoxCrawler initialisé avec succès")
        logger.info(f"- geckodriver = {GECKODRIVER_PATH}")
        #logger.info(f"- max_pages = {max_pages}") # @todo transformer en max avant de recharger une instance Firefox
        logger.info(f"- max_cloudflare_errors = {max_cloudflare_errors}")
        logger.info(f"- min_delay = {min_delay}")
        logger.info(f"- max_delay = {max_delay}")
        logger.info(f"- headless = {headless}")

    def _init_driver(self):
        """Initialise le driver Firefox avec options avancées."""
        options = Options()

        if self.headless:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")

        # Configuration pour éviter la détection
        ua = UserAgent()
        options.set_preference("general.useragent.override", ua.random)
        options.set_preference("javascript.enabled", True)
        options.set_preference("network.cookie.cookieBehavior", 0)  # Accepte tous les cookies
        options.set_preference("dom.webdriver.enabled", False)  # Désactive le flag webdriver

        # Configuration du proxy si fourni
        if self.proxy_list:
            self._configure_proxy(options)

        # Initialisation du service et du driver avec le chemin fixe
        service = Service(executable_path=GECKODRIVER_PATH)
        self.driver = webdriver.Firefox(service=service, options=options)

        # Redimensionne la fenêtre pour un comportement réaliste
        self.driver.set_window_size(1280, 800)

    def _configure_proxy(self, options):
        """Configure un proxy pour le driver."""
        proxy = self.proxy_list[self.current_proxy_index]
        proxy_ip, proxy_port = proxy.split(":")
        options.set_preference("network.proxy.type", 1)
        options.set_preference("network.proxy.http", proxy_ip)
        options.set_preference("network.proxy.http_port", int(proxy_port))
        options.set_preference("network.proxy.ssl", proxy_ip)
        options.set_preference("network.proxy.ssl_port", int(proxy_port))
        logger.info(f"Proxy configuré: {proxy}")

    def _rotate_proxy(self):
        """Passe au proxy suivant dans la liste."""
        if not self.proxy_list:
            return
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        logger.info(f"Rotation vers le proxy: {self.proxy_list[self.current_proxy_index]}")
        self._init_driver()  # Recharge le driver avec le nouveau proxy

    def _hide_automation(self):
        """Masque les propriétés d'automatisation pour éviter la détection."""
        """
        AVANT :
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        // Masque navigator.webdriver

        
                    // Simule des plugins réalistes
            // Simule des langues réalistes
            // Masque la propriété webdriver dans navigator

        """
        #self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name: 'Chrome PDF Plugin', description: 'Portable Document Format', filename: 'internal-pdf-viewer'},
                    {name: 'Chrome PDF Viewer', description: '', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                    {name: 'Native Client', description: '', filename: 'internal-nacl-plugin'}
                ]
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['fr-FR', 'fr', 'en-US', 'en']
            });
            """)
        #self.driver.execute_script("""
        #    Object.defineProperty(navigator, 'webdriver', {
        #        get: () => false
        #    });
        #""")

        # Masque aussi via CDP (Chrome DevTools Protocol)
        #try:
        #    self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        #        "source": """
        #            Object.defineProperty(navigator, 'webdriver', {
        #                get: () => undefined
        #            });
        #        """
        #    })
        #except WebDriverException:
        #    logger.debug("CDP non disponible (Firefox standard).")

    def _random_human_delay(self, min_sec=0.5, max_sec=3.0):
        """Génère un délai aléatoire selon une distribution réaliste."""
        return random.triangular(min_sec, max_sec, (min_sec + max_sec) / 2)

    def _sanitize_filename(self, url):
        """Nettoie l'URL pour en faire un nom de fichier valide."""
        filename = url.replace("https://", "").replace("http://", "")
        filename = filename.replace("/", ".").replace("&", ".").replace("?", ".")
        return filename[:150]  # Limite la longueur

    def _get_cache_paths(self, url):
        """Retourne les chemins des fichiers cache."""
        filename = self._sanitize_filename(url)
        html_path = os.path.join(self.cache_dir, f"{filename}.html")
        url_path = os.path.join(self.cache_dir, f"{filename}.url.txt")
        cookie_path = os.path.join(self.cache_dir, f"{filename}.cookies.json")
        return html_path, url_path, cookie_path

    def _load_from_cache(self, url):
        """Charge le contenu HTML et les cookies depuis le cache."""
        html_path, _, cookie_path = self._get_cache_paths(url)
        if os.path.exists(html_path):
            with open(html_path, "r", encoding="utf-8") as f:
                self.nb_cached_pages += 1
                html_content = f.read()

            # Charge les cookies si disponibles
            if os.path.exists(cookie_path):
                with open(cookie_path, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                    for cookie in cookies:
                        try:
                            self.driver.add_cookie(cookie)
                        except Exception as e:
                            logger.debug(f"Erreur chargement cookie: {e}")
                logger.debug(f"Cookies restaurés pour {url}")
            return html_content
        return None

    def _save_to_cache(self, url, html_content):
        """Sauvegarde le contenu HTML et les cookies dans le cache."""
        html_path, url_path, cookie_path = self._get_cache_paths(url)

        # Sauvegarde le HTML
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        with open(url_path, "w", encoding="utf-8") as f:
            f.write(url)

        # Sauvegarde les cookies
        cookies = self.driver.get_cookies()
        if cookies:
            with open(cookie_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f)
            logger.debug(f"Cookies sauvegardés pour {url}")

    def _handle_cookie_button(self):
        """Accepte les cookies (ex: Tarte au Citron, RGPD)."""
        try:
            # Bouton Tarte au Citron
            cookie_button = self.driver.find_element(By.ID, "tarteaucitronPersonalize2")
            logger.info("Bouton d'acceptation des cookies détecté (Tarte au Citron).")
            self.driver.execute_script("arguments[0].scrollIntoView();", cookie_button)
            time.sleep(self._random_human_delay(0.5, 1.5))
            self.nb_cookies_click += 1
            cookie_button.click()
            time.sleep(self._random_human_delay(1, 2))
            return True
        except Exception:
            try:
                # Autres boutons courants (RGPD, etc.)
                cookie_buttons = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Accepter') or contains(text(), 'OK') or contains(text(), 'Consent')]")
                if cookie_buttons:
                    cookie_button = random.choice(cookie_buttons)
                    logger.info("Bouton d'acceptation des cookies détecté (générique).")
                    self.driver.execute_script("arguments[0].scrollIntoView();", cookie_button)
                    time.sleep(self._random_human_delay(0.5, 1.5))
                    self.nb_cookies_click += 1
                    cookie_button.click()
                    time.sleep(self._random_human_delay(1, 2))
                    return True
            except Exception:
                pass
        return False

    def _simulate_human_mouse_movement(self):
        """Simule un déplacement de souris réaliste en cercle (10 étapes, 3s total)."""
        try:
            logger.info("Simulation d'un déplacement de souris (cercle)...")
            window_size = self.driver.get_window_size()
            center_x, center_y = window_size['width'] // 2, window_size['height'] // 2
            radius = min(window_size['width'], window_size['height']) // 3
            steps = 10
            delay = 3.0 / steps  # 0.3s par étape

            actions = ActionChains(self.driver)
            last_x = last_y = 0

            for i in range(steps + 1):
                angle = 2 * math.pi * i / steps
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)

                if last_x == 0:
                    actions.move_by_offset(x, y)
                else:
                    actions.move_by_offset(x - last_x, y - last_y)
                actions.perform()
                time.sleep(delay)
                last_x, last_y = x, y

            logger.info("Déplacement de souris terminé.")
            return True
        except Exception as e:
            logger.error(f"Erreur simulation souris: {e}")
            return False

    def _simulate_human_interactions(self):
        """Simule des interactions humaines aléatoires (clics, scrolls)."""
        try:
            # Scroll aléatoire
            for _ in range(random.randint(1, 3)):
                self.driver.execute_script(f"window.scrollBy(0, {random.randint(100, 300)})")
                time.sleep(self._random_human_delay(0.3, 1.0))

            # Clic aléatoire sur un lien visible
            links = self.driver.find_elements(By.TAG_NAME, "a")
            if links:
                visible_links = [link for link in links if link.is_displayed()]
                if visible_links:
                    random_link = random.choice(visible_links)
                    self.driver.execute_script("arguments[0].scrollIntoView();", random_link)
                    time.sleep(self._random_human_delay(0.5, 1.0))
                    random_link.click()
                    time.sleep(self._random_human_delay(1, 2))
                    self.driver.back()  # Retour à la page précédente
                    time.sleep(self._random_human_delay(1, 2))
        except Exception as e:
            logger.debug(f"Interaction humaine échouée: {e}")

    def _handle_cloudflare_challenge(self):
        """Gère les challenges Cloudflare avec détection améliorée."""
        try:
            page_source = self.driver.page_source.lower()
            if ("challenges.cloudflare" in page_source or
                "just a moment" in page_source or
                "checking your browser" in page_source or
                "cloudflare" in page_source):

                logger.warning("Challenge Cloudflare détecté. Tentative de contournement...")
                time.sleep(self._random_human_delay(1, 2))

                # Simulation de souris
                if not self._simulate_human_mouse_movement():
                    return False

                time.sleep(self._random_human_delay(1, 2))

                # Soumission du formulaire si présent
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
                    submit_button.click()
                    time.sleep(self._random_human_delay(2, 3))
                except Exception:
                    pass

                # Rechargement de la page
                self.driver.refresh()
                time.sleep(self._random_human_delay(3, 5))
                return True
        except Exception as e:
            logger.error(f"Erreur gestion Cloudflare: {e}")
            return False

    def fetch_page(self, url):
        """
        Récupère le contenu d'une page avec gestion des cookies, challenges et comportements humains.

        Args:
            url (str): URL de la page à récupérer.

        Returns:
            str: Contenu HTML de la page, ou None en cas d'échec.
        """
        # Vérifie d'abord le cache
        cached_html = self._load_from_cache(url)
        if cached_html:
            logger.info(f"Lecture en cache pour {url}")
            return cached_html

        try:
            logger.info(f"Lecture web pour {url}")
            # Délai aléatoire avant la requête
            time.sleep(self._random_human_delay())

            logger.info(f"Chargement de {url}...")
            self.driver.get(url)

            # Gestion des cookies
            self._handle_cookie_button()

            # Gestion des challenges Cloudflare
            #self._handle_cloudflare_challenge() # J'abandonne la tentative de gérer les challenges Cloudflare

            # Attend que la page soit chargée
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Vérifie si Cloudflare persiste
            if ("challenges.cloudflare" in self.driver.page_source.lower() or
                "just a moment" in self.driver.page_source.lower()):
                #logger.error("Challenge Cloudflare persistant après tentative de contournement.")
                self.nb_cloudflare_errors += 1
                logger.error(f"Challenge Cloudflare détecté ({self.nb_cloudflare_errors}/{self.max_cloudflare_errors}).")
                if self.nb_cloudflare_errors >= self.max_cloudflare_errors:
                    logger.error(f"Arrêt après {self.max_cloudflare_errors} challenges Cloudflare détectés.")
                    self.abort_crawling = True
                self._rotate_proxy()  # Change de proxy
                return None

            # Simule des interactions humaines
            self._simulate_human_interactions()

            # Récupère le contenu
            html_content = self.driver.page_source
            self._save_to_cache(url, html_content)
            self.nb_scanned_pages += 1
            logger.info(f"Page chargée avec succès: {url}")
            return html_content

        except Exception as e:
            logger.error(f"Erreur lors du chargement de {url}: {str(e)[:200]}...", exc_info=True)
            self.nb_crawling_errors += 1
            self._rotate_proxy()  # Change de proxy en cas d'erreur
            return None

    def add_link(self, url, meta=None):
        """
        Ajoute un lien à la file d'attente si non déjà visité.

        Args:
            url (str): URL à ajouter.
            meta (dict): Métadonnées associées. Default: None.

        Returns:
            bool: True si le lien a été ajouté, False sinon.
        """
        if meta is None:
            meta = {}
        if url not in self.visited_urls and url not in [item[0] for item in list(self.queue.queue)]:
            self.queue.put((url, meta))
            logger.debug(f"Lien ajouté à la file: {url}")
            return True
        return False

    def crawl(self, start_url, meta=None):
        """
        Lance le crawling en partant d'une URL de départ.

        Args:
            start_url (str): URL de départ.
            meta (dict): Métadonnées initiales. Default: None.
        """
        if meta is None:
            meta = {}
        self.add_link(start_url, meta)
        pages_visited = 0

        while not self.queue.empty() and self.abort_crawling == False:
            url, meta = self.queue.get()
            if url in self.visited_urls:
                continue
            self.visited_urls.add(url)
            pages_visited += 1
            logger.info(f"Visite page #{pages_visited} {url}")

            html_content = self.fetch_page(url)
            if html_content:
                self.parse_page(url, html_content, meta)

    def parse_page(self, url, html_content, meta):
        """
        Méthode à surcharger pour le parsing du contenu des pages.
        Par défaut, ne fait rien.

        Args:
            url (str): URL de la page.
            html_content (str): Contenu HTML de la page.
            meta (dict): Métadonnées associées.
        """
        pass

    def close(self):
        """Fermeture du driver et affichage des statistiques."""
        self.driver.quit()
        #logger.info("="*50)
        logger.info("Statistiques de crawling :")
        #logger.info("="*50)
        logger.info(f"- pages scannées (Internet)       : {self.nb_scanned_pages}")
        logger.info(f"- pages lues en cache             : {self.nb_cached_pages}")
        logger.info(f"- nb cookies acceptés             : {self.nb_cookies_click}")
        logger.info(f"- erreurs Cloudflare persistantes : {self.nb_cloudflare_errors}")
        logger.info(f"- erreurs de crawling             : {self.nb_crawling_errors}")
        #logger.info("="*50)
