import logging
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException
from typing import Optional

geckodriver_installation_path="C:\\Programs\\GeckoDriver\\geckodriver.exe"

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Affiche les logs dans la console
        logging.FileHandler('tmp/html_fetcher.log')  # Sauvegarde les logs dans un fichier
    ]
)
logger = logging.getLogger(__name__)

class HTMLFetchError(Exception):
    """Exception personnalisée pour les erreurs de récupération HTML."""
    pass

class FileSaveError(Exception):
    """Exception personnalisée pour les erreurs de sauvegarde de fichier."""
    pass

def get_html_content(url: str, geckodriver_path: Optional[str] = geckodriver_installation_path, headless: bool = True) -> str:
    """
    Ouvre une page web avec Firefox en mode headless et retourne son contenu HTML.

    Args:
        url (str): URL de la page à récupérer.
        geckodriver_path (str, optionnel): Chemin vers geckodriver. Si None, utilise le PATH système.
        headless (bool, optionnel): Si True, exécute en arrière-plan. Par défaut True.

    Returns:
        str: Contenu HTML de la page.

    Raises:
        HTMLFetchError: En cas d'erreur de connexion, timeout ou problème avec WebDriver.
    """
    logger.info(f"Récupération du contenu HTML pour l'URL : {url}")
    options = Options()
    if headless:
        options.add_argument("--headless")
        logger.info("Mode headless activé.")

    try:
        geckodriver_path = geckodriver_installation_path # forçage (visiblement, ce n'est pas bien passé...)
        logger.info(f"geckodriver_path = '{geckodriver_path}'")
        service = Service(executable_path=geckodriver_path) if geckodriver_path else Service()
        driver = webdriver.Firefox(service=service, options=options)
        logger.info("WebDriver initialisé avec succès.")
    except WebDriverException as e:
        logger.error(f"Erreur lors de l'initialisation du WebDriver : {e}")
        raise HTMLFetchError(f"Erreur lors de l'initialisation du WebDriver : {e}")

    try:
        logger.info(f"Ouverture de la page : {url}")
        driver.get(url)
        logger.info("Page chargée avec succès.")
        return driver.page_source
    except TimeoutException as e:
        logger.error(f"Timeout lors de la récupération de la page {url} : {e}")
        raise HTMLFetchError(f"Timeout lors de la récupération de la page {url} : {e}")
    except WebDriverException as e:
        logger.error(f"Erreur lors de la récupération de la page {url} : {e}")
        raise HTMLFetchError(f"Erreur lors de la récupération de la page {url} : {e}")
    finally:
        driver.quit()
        logger.info("WebDriver fermé.")

def save_html_to_file(url: str, output_file: str, geckodriver_path: Optional[str] = None, headless: bool = True) -> None:
    """
    Récupère le contenu HTML d'une page et le sauvegarde dans un fichier.

    Args:
        url (str): URL de la page à récupérer.
        output_file (str): Chemin du fichier de sortie.
        geckodriver_path (str, optionnel): Chemin vers geckodriver. Si None, utilise le PATH système.
        headless (bool, optionnel): Si True, exécute en arrière-plan. Par défaut True.

    Raises:
        HTMLFetchError: En cas d'erreur de récupération HTML.
        FileSaveError: En cas d'erreur de sauvegarde du fichier.
    """
    logger.info(f"Début de la sauvegarde du contenu HTML de {url} vers {output_file}.")
    try:
        html_content = get_html_content(url, geckodriver_path, headless)
        logger.info("Contenu HTML récupéré avec succès.")
    except HTMLFetchError as e:
        logger.error(f"Échec de la récupération du contenu HTML : {e}")
        raise

    try:
        logger.info(f"Sauvegarde du contenu HTML dans {output_file}.")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"Contenu HTML enregistré avec succès dans '{output_file}'.")
    except IOError as e:
        logger.error(f"Erreur lors de la sauvegarde du fichier {output_file} : {e}")
        raise FileSaveError(f"Erreur lors de la sauvegarde du fichier {output_file} : {e}")

# Exemple d'utilisation avec gestion des erreurs et logs
if __name__ == "__main__":
    #url = "https://www.google.com/"  # Remplace par l'URL souhaitée
    url = "https://gw.geneanet.org/dbrigitte6?lang=fr&p=francoise&n=durand&type=fiche"  # Remplace par l'URL souhaitée
    output_file = "tmp/page_content.html"  # Nom du fichier de sortie

    try:
        save_html_to_file(url, output_file)
    except HTMLFetchError as e:
        logger.critical(f"Échec de la récupération du contenu HTML : {e}")
    except FileSaveError as e:
        logger.critical(f"Échec de la sauvegarde du fichier : {e}")
    except Exception as e:
        logger.critical(f"Erreur inattendue : {e}")
