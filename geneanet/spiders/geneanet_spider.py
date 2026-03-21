# -*- coding: utf-8 -*-
import os

#import scrapy
from scrapy import signals
import html2text
import logging
#from scrapy.utils.log import configure_logging
import gedcomw
from gedcomw.parser import Parser
import gedcomw.element
from gedcomw.element.individual import IndividualElement
from datetime import datetime
#import sys
#import atexit
import shutil # pour copyfile final
#import time # pour pause
import re
import tempfile
from crawler import FirefoxCrawler
from scrapy.http import HtmlResponse
#from scrapy.selector import Selector
import sys
import argparse

# Configuration fichier de sortie log :
# problème : il faut le faire ici, sinon on rate le début du log (et ça ne marche pas dans start_requests)
# mais on n'a pas encore l'url, à partir de laquelle on veut construire le nom du log.
# Contournement : on écrit dans un log tmp et on renomme à la fin...
tmplogfile = tempfile.NamedTemporaryFile(suffix=".log.tmp", prefix="fscrapy.", dir="tmp", delete=False)
tmplogfile.close() # selon Le Chat : "évite le double descripteur ouvert (important sur Windows)."
# configure_logging(install_root_handler=False)
#logging.basicConfig(
#    #filename=tmplogfile,
#    # format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
#    format='[%(name)s] %(levelname)s: %(message)s',
#    encoding='utf-8', # sinon les grep (de git bash) dans les logs ne fonctionnent pas sur les lignes accentuées !
#    level=logging.DEBUG
#)

# Handler stdout
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(FirefoxCrawler.get_formatter())
# Handler fichier
file_handler = logging.FileHandler(tmplogfile.name)
file_handler.setFormatter(FirefoxCrawler.get_formatter())
logger = logging.getLogger("GeneanetSpider")  # Logger NRa
logger.propagate = False  # ← ne remonte pas au root logger
logger.addHandler(stream_handler)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)
logging.getLogger("FirefoxCrawler").addHandler(file_handler)
#print('Logger GeneanetSpider initialisé.', flush=True)


class GeneanetSpider(FirefoxCrawler):
    name = "geneanet"
    progname = "GeneanetFSpider" # "F" comme Firefox
    version = "2.0.0" # v1.0.26 = dernière version avec Scrapy. v2.x = version Selenium/Firefox
    team = "Nicolas Raibaut"
    address = "raibaut.nicolas@gmail.com" # "https://xxxxxx"
    result_dir = "result"
    result_name = "tbd.tmp" # sera connu plus tard
    nb_persons = 0
    nb_alias = 0
    nb_masked_persons = 0
    nb_families = 0
    nb_consanguinites = 0
    nb_titres_noblesse = 0
    nb_notes_titres_noblesse = 0
    lg_min_notes_longues = 60
    nb_notes_longues = 0
    nb_sous_titres = 0
    multiple_events_count = 0
    max_generations = 0
    nb_errors = 0
    nb_todo = 0
    parents_of = {} # dictionnaire des parents de chaque individu (index = <true_url_enfant>)
    pointer_of = {} # dictionnaire des pointeurs (id) de chaque individu (index = <true_url>)
    sex_of = {} # dictionnaire des sexes des parents de chaque individu (index = <true_url>)
    mariages_dates = {} # dictionnaire des dates de mariaqes (index = "<true_url_pere>;<true_url_mere>")
    mariages_places = {} # dictionnaire des lieux de mariages (index = "<true_url_pere>;<true_url_mere>")
    mariages_sources = {} # dictionnaire des sources de mariages (index = "<true_url_pere_ou_mere>")
    mariages_note_union = {} # dictionnaire des notes sur les unions (index = "<true_url_pere>;<true_url_mere>")
    true_url_of = {} # dictionnaire des url (index = <pointer>)
    is_http_url = re.compile("^http[s]*:.*")
    #is_file_url = re.compile("^file:.*")
    is_mariage = re.compile("^Mariage \(avec .*\).*")
    is_contrat_de_mariage = re.compile("^Contrat de mariage \(avec .*\).*")
    ligne_mariage = re.compile(".*Mari.*avec.*")
    union_regex = re.compile("(.*) [Aa]vec \[([^\]]*)\]\(([^\)]*)\).*")
    union_avec_regex = re.compile("Union avec.*")

    paragraphes_connus = [
        "Aperçu de l'arbre",
        "Demi-frères et demi-sœurs",
        "Fratrie",
        "Grands parents maternels, oncles et tantes",
        "Grands parents paternels, oncles et tantes",
        "Notes concernant l'union",
        "Notes",
        "Parents",
        "Photos & documents",
        "Relations",
        "Sources",
        "Union(s) et enfant(s)",
        "Union(s)",
        "Union(s), enfant(s)",
        "Événements",
        "Présences lors d'événements",
        "Arbre généalogique (aperçu)" # nouveau mars 2026
    ]

    #def __init__(self, max_pages=50)
    def __init__(self, max_pages=50, max_cloudflare_errors=10, min_delay=0.5, max_delay=2.0, headless=False):

        logger.info(f"Starting {self.progname} {self.version}")
        super().get_logger().addHandler(file_handler)
        super().__init__(max_pages=max_pages, max_cloudflare_errors=max_cloudflare_errors, min_delay=min_delay, max_delay=max_delay, headless=headless)

        # Initialize the parser
        self.gedcomw_parser = None
        self.logger = logger # pour compatibilité ascendante v1.x

        logger.info(f"Init {self.progname} {self.version} OK")

    def url_to_filename(self, url):
        result = url
        #result = result.replace("https://", "")
        result = re.sub("^http[s]*://", "", result)
        result = re.sub("^file:.*/pages/", "", result)
        result = re.sub("^file:.*.pages.", "", result)
        result = result.replace("/", ".")
        result = result.replace("\\", ".")
        result = result.replace("&", ".")
        result = result.replace("?", ".")
        result = result.replace("%", "_") # ex : https://gw.geneanet.org/boutch1?lang=fr&pz=marc&nz=vitelli&p=be%CC%81atrice+marguerite&n=de+faucigny
        return result

    def url_to_true_http_url(self, current_true_http_url, url_to_scan):
        """
        Renvoie l'url à parser : celle en cache si on l'a déjà, sinon la vraie url
        :param url:
        :return:
        """
        # current_true_http_url = forcément une vraie URL http (https://...)
        # url_to_scan =
        # * soit une vraie URL http (https://...)
        # * soit quelque chose de la forme "file:///compte?lang=fr&p=pierre&n=dupont"

        is_http_url = GeneanetSpider.is_http_url.match(url_to_scan)
        if is_http_url:
            result = url_to_scan
        else:
            part1 = re.sub("[^/]*$", "", current_true_http_url) # on coupe après le dernier "/"
            part2 = re.sub(".*/", "", url_to_scan) # on coupe jusqu'au dernier "/"
            result = part1 + part2

        return result

    def get_url_to_scan(self, true_http_url):
        """
        Historiquement : Renvoie l'url à parser : celle en cache si on l'a déjà, sinon la vraie url
        A partir v2.0 / fev 2026 : adapte si besoin en ajoutant "&type=fiche" (absent du texte html, mais ajouté à la volée par l'IHM
        :param url:
        :return:
        """
        # url = forcément une vraie URL http (https://...)
        result = true_http_url    # par défaut

        if not "&type=fiche" in result:
            logger.info(f"Patch type=fiche pour {result}")
            result = result + "&type=fiche"

        return result
    def patch_url(self, url):
        result = url
        # mars 2025 : beaucoup d'erreurs 403, dont certaines systématiques sur des url contenant "&iz=12"
        # (cas arbo https://gw.geneanet.org/jvo2506?lang=fr&n=van+brussel&oc=0&p=eduardus : https://gw.geneanet.org/jvo2506?lang=fr&iz=12&p=maria+joanna&n=pieters)
        # Etrangement, en supprimant ce champ "iz=", les erreurs disparaissent...
        result = re.sub("&iz=[^&]*", "", result)  # suppression "&iz=xxx"
        # complément avril 2025 : même problème avec "&pz=xxx" et "&nz=xxx"
        # (cas arbo https://gw.geneanet.org/evechevaleyre?lang=fr&n=brincat&oc=0&p=maria+anna)
        result = re.sub("&pz=[^&]*", "", result)  # suppression "&pz=xxx"
        result = re.sub("&nz=[^&]*", "", result)  # suppression "&nz=xxx"
        result = re.sub("&ocz=[^&]*", "", result)  # suppression "&ocz=xxx"

        return result

    def key_union(self, url_parent1, url_parent2):
        """
        Donne la clé à utiliser pour les dictionnaires concernant les mariages.
        Au lieu d'utiliser url_pere/url_mere (en risquant de se tromper), on trie pa ordre alphabétique
        :param url_parent1:
        :param url_parent2:
        :return:
        """
        url_parent1b = self.patch_url(url_parent1) # robustesse : ne pas considérer "&pz=xxxx&nz=xxxx" , "&iz=xxx" dans la clé
        url_parent2b = self.patch_url(url_parent2)
        if url_parent1b > url_parent2b:
            result = url_parent1b + ";" + url_parent2b
        else:
            result = url_parent2b + ";" + url_parent1b
        return result

    def set_parent_of(self, child_true_url, parent_true_url):
        if child_true_url not in self.parents_of:
            self.parents_of[child_true_url] = [parent_true_url]
        else:
            self.parents_of[child_true_url].append(parent_true_url)

    def post_trt_notes(self, texte):
        """
        Post-traitement des notes, notamment pour faire le ménage des datas superflues
        de la généalogie https://gw.geneanet.org/boutch1?lang=fr&n=revest&oc=0&p=gregorio
        :param texte:
        :return:
        """
        result = texte + "\n" # pour permettre l'éventuel match de la dernière ligne
        result = result.replace(u"\u00A0", " ")  # avant toute chose !

        # Lignes "\-- GEDCOM (INDI) -- 1 SUBM @S6000000001808673965@" :
        result = re.sub("([^\n]* GEDCOM .INDI. [^\n]*)\n", "", result )
        # Lignes "  1 SUBM @S2304562@" :
        result = re.sub("([ 0-9]* SUBM @S[0-9]*@ *)\n", "", result )

        result = re.sub(" *\n", "\n", result)  # suppression des espaces inutiles en fin de lignes
        result = re.sub("\n\\\\", "\n", result)  # suppression des caractères "\" en début de lignes

        result = re.sub("^[\n ]*", "", result )  # Espaces / retours chariot en trop au début
        result = re.sub("[\n ]*$", "", result )  # Espaces / retours chariot en trop à la fin

        return result
    def post_trt_sources(self, texte):
        """
        Post-traitement des sources, notamment pour faire le ménage des datas superflues
        de la généalogie https://gw.geneanet.org/boutch1?lang=fr&n=revest&oc=0&p=gregorio
        :param texte:
        :return:
        """
        result = texte + "\n" # pour permettre l'éventuel match de la dernière ligne
        result = result.replace(u"\u00A0", " ")  # avant toute chose !

        # Lignes "\- - 26 APR 2021 - First Name" :
        result = re.sub("(\\\\*- - [0-9]+ [A-Z]+ [0-9]+ - [^\n]*)\n", "", result )

        result = re.sub(" *\n", "\n", result)  # suppression des espaces inutiles en fin de lignes

        result = re.sub("^[\n ]*", "", result )  # Espaces / retours chariot en trop au début
        result = re.sub("[\n ]*$", "", result )  # Espaces / retours chariot en trop à la fin

        return result

    def start(self, start_url):
        result_name = self.url_to_filename(start_url)
        GeneanetSpider.result_name = result_name

        logger.info(f"Starting parsing : start_url = {start_url}")
        logger.info(f"result_name = {result_name}")

        # Initialisation parser
        self.gedcomw_parser = Parser()

        self.gedcom_result_filename = result_name + ".ged"
        logger.info(f"gedcom_result_filename = {self.gedcom_result_filename}")
        now = datetime.now()  # current date and time
        date = now.strftime("%d/%m/%Y à %H:%M")
        header_text = f"Cette généalogie a été créée par {self.progname} {self.version} le {date} à partir de {start_url}"
        self.gedcomw_parser.nra_set_header(header_text, self.progname, self.version, self.progname,
                   self.team, self.address, self.gedcom_result_filename)

        # Sorties CSV :
        csvfilename = self.result_dir + "/" + result_name + ".persons.csv"
        logger.info(f"csv persons = {csvfilename}")
        self.csv = open( csvfilename, "w", encoding="utf-8")
        self.csv.write(f"generation;sosa;id;prenom;nom;sexe;source;nb_infos;nb_evenements;nb_sources;nb_parents;forme_parents;parents_mariage_date;parents_mariage_lieu;profession;sous_titre;titre_noblesse;note_titre_noblesse;nb_notes;nb_notes_longues;infos;nb_err;{self.progname} {self.version} {date}\n")

        csvfilename = self.result_dir + "/" + result_name + ".events.csv"
        logger.info(f"csv events = {csvfilename}")
        self.csv_events = open( csvfilename, "w", encoding="utf-8")
        self.csv_events.write(f"id;prenom;nom;url;evenement;tag;date;gedcom_date;lieu;notes;tag_ou_type;source;notes_source;{self.progname} {self.version} {date}\n")

        csvfilename = self.result_dir + "/" + result_name + ".unions.csv"
        logger.info(f"csv unions = {csvfilename}")
        self.csv_unions = open( csvfilename, "w", encoding="utf-8")
        self.csv_unions.write(f"id;prenom;nom;url;origine;url_pere;url_mere;date;lieu;debug;{self.progname} {self.version} {date}\n")

        url_to_scan = self.get_url_to_scan(start_url)
        logger.info(f"Root URL = {start_url} (to_scan='{url_to_scan}')")

        #yield scrapy.Request(url=url_to_scan, callback=self.parse, meta={'generation':0, 'sosa':1, 'true_http_url':true_url}, headers=self.HEADERS)
        """Démarre le crawl avec l'URL de départ et métadonnées initiales."""
        self.crawl(start_url, meta={'generation': 0, 'sosa': 1})
        self.close()

    def parse_page(self, url, html_content, meta):

        #def parse(self, response):
        #url_source = response.request.url
        # avant (v1.x) : soit une "vraie" url (https://...) soit un fichier (file://...)
        # maintenant (v2.x) : géré par le crawler, toujours https://...
        true_http_url = url_source = url
        response = HtmlResponse(
            url=url,
            body=html_content.encode('utf-8'),  # Le contenu doit être en bytes
            encoding='utf-8',
        )
        nb_infos = 0
        texte_infos = ""

        # is_http_url = GeneanetSpider.is_http_url.match(url_source)
        # désormais inutile
        # self.nb_scanned_pages et self.nb_cached_pages calculés par le crawler
        # + mise en cache faite par le crawler

        if true_http_url == "https://www.geneanet.org/bots/firewall":
            self.nb_errors += 1
            self.logger.error(f"Blocage robot : url='{true_http_url}' --> utiliser un VPN !")
            return # ne pas aller plus loin dans le parsing de la page !

        generation = meta['generation'] + 1
        if generation > self.max_generations :
            self.max_generations = generation
        sosa = meta['sosa']
        self.nb_persons += 1
        pointer = "@I%05d@" % (self.nb_persons)
        self.pointer_of[true_http_url] = pointer # on mémorise pour plus tard (élaboration des familles)
        nb_errors_indiv = 0

        #generation = 1
        #prenom = response.xpath("//div[@id='person-title']//div//h1//a//text()")[0].extract()
        #nom = response.xpath("//div[@id='person-title']//div//h1//a//text()")[1].extract()
        #prenom = response.xpath("//div[@id='person-title']//div//h1//a[1]//text()")[0].extract()
        #nom = response.xpath("//div[@id='person-title']//div//h1//a[2]//text()")[0].extract()
        prenom = response.xpath("//div[@id='person-title']/div/h1/a[1]/text()").get()
        nom = response.xpath("//div[@id='person-title']/div/h1/a[2]/text()").get()
        extraire_surnom = False # cas avec surnom en tête, et liens nom/prénom plus loin
        if prenom is None:
            prenom = response.xpath("//div[@id='person-title']/../*/a[contains(@href,'&m=P&')]/text()").get() # lien hypetexte contenant "&m=P&" (recherche par prénom)
            extraire_surnom = True
        if nom is None:
            nom = response.xpath("//div[@id='person-title']/../*/a[contains(@href,'&m=N&')]/text()").get() # lien hypetexte contenant "&m=N&" (recherche par nom)
            extraire_surnom = True
        # Certains noms/prénoms sont à côté de "div[@id='person-title'", mais avec un niveau "span" supplémentaire
        if prenom is None:
            prenom = response.xpath("//div[@id='person-title']/..//a[contains(@href,'&m=P&')]/text()").get()  # lien hypetexte contenant "&m=P&" (recherche par prénom)
            extraire_surnom = True
        if nom is None:
            nom = response.xpath("//div[@id='person-title']/..//a[contains(@href,'&m=N&')]/text()").get()  # lien hypetexte contenant "&m=N&" (recherche par nom)
            extraire_surnom = True
        if prenom is None and nom is None:
            # Cas personne masquée ?
            is_masked = response.xpath("//span[@class='masked-person']/text()").get()
            #if is_masked == "\nPersonne masquée":
            if is_masked != None:
                prenom = "?"
                nom = "?"
                texte_infos = texte_infos + "Personne masquée\n"
                self.nb_masked_persons += 1
                extraire_surnom = False
        if prenom is None :
            nb_errors_indiv += 1
            self.logger.error(f"Pas pu extraire le prénom pour {true_http_url} !")
            prenom = "????"
        if nom is None:
            nb_errors_indiv += 1
            self.logger.error(f"Pas pu extraire le nom pour {true_http_url} !")
            nom = "????"
        prenom = re.sub("^\.\.*\.$", "?", prenom) # cas de certains prénoms valant "..." --> vide
        nom = re.sub("^\.\.*\.$", "?", nom) # cas de certains prénoms valant "..." --> vide
        nom = nom.upper() # Nom en majuscules
        if extraire_surnom:
            surnom = html2text.html2text(response.xpath("//div[@id='person-title']/div/h1/em").get()) # on tente d'extraire la partie "em"
            if surnom is None:
                surnom = html2text.html2text(response.xpath("//div[@id='person-title']/div/h1").get())
                # Exemple : "#  ![H](images/male.png) Jean GINOUX _dit le vieux_"
            surnom = surnom.replace(u"\u00A0", " ")  # avant toute chose !
            surnom = re.sub(".*\.png\) *", "", surnom) # suppression image de début
            surnom = re.sub("_", "", surnom) # suppression caractères de formatage
            surnom = surnom.strip()

            texte_infos = texte_infos + "- surnom: " + surnom + '\n'
            logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : surnom='{surnom}'")


        sexe = response.xpath("//div[@id='person-title']/div/h1/img/@title").get() # "H/F" en français, "M/F" en anglais
        if sexe == None:
            sexe = response.xpath("//div[@id='person-title']/div/h1/img/@alt").get() # "Homme" ou "Femme" en français # nouveau format mars 2026
        if sexe == "Homme" :
           sexe = "M"
        elif sexe == "Femme":
           sexe = "F"
        elif sexe == "H" :
            sexe = "M"
        if sexe not in ("M", "F") :
            nb_errors_indiv += 1
            self.logger.error(f"Sex ({sexe}) is not 'M' or 'F' for {prenom} {nom} ({true_http_url}) !")
        self.sex_of[true_http_url] = [sexe]

        # Dans la section "<span ng-non-bindable>" juste après le nom, on peut avoir des infos supplémentaires "sous-titre".
        # Chaque ligne est une balise "em".
        # Cette section se termine par "<br class="separateur"><br >".
        # Ignorer les éventuelles lignes "(<a href="boutch1?lang=fr&pz=marc&nz=vitelli&m=P&v=agnes">Agnès</a>", déjà traitées par ailleurs.
        #for info in response.xpath("//div[@id='person-title']/following-sibling::span[1]/em"):
        for info in response.xpath("//div[@id='person-title']/following-sibling::span[count(br[@class='separateur'])>0]/em[count(a/@href)=0]"):
            line = html2text.html2text(info.get()).strip()
            line = re.sub("^\* *", "", line)
            line = line.replace(u"\u00A0", " ")  # avant toute chose !
            line = re.sub(" * ", " ", line) # suppression espaces multiples
            line = re.sub("_", "", line) # suppression caractères de formatage
            line = re.sub("^, *", "", line) # suppression ", " en début de ligne
            if len(line) > 0:
                self.nb_alias += 1
                logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : info sous-titre / alias = '{line}'")
                texte_infos = texte_infos + "* " + line + '\n'

        # Tentative (KO) de pause pour limiter erreurs "Redirecting (302) to ..." / "Forbidden by robots.txt: ..."
        #pause = 0
        #if generation >= 3 :
        #    pause = 2 ** generation
        #    #pause = 1000
        #    pause = 0
        #    time.sleep(pause/1000)
        logger.info(f"Generation {generation}, sosa {sosa}, id {pointer} : '{prenom}' '{nom}' ({sexe}) ({true_http_url})")
        self.true_url_of[pointer] = true_http_url # pour retrouver les infos sur les mariages

        source_personne = None
        person = IndividualElement(0, pointer, gedcomw.tags.GEDCOM_TAG_INDIVIDUAL, "", '\n', multi_line=False)
        person.set_name(prenom,nom)
        person.set_sex(sexe)
        self.gedcomw_parser.get_root_element().add_child_element(person)

        profession = None
        #for info in response.xpath("//div[@id='person-title']/following-sibling::ul[1]/li/text()"):
        for info in response.xpath("//div[@id='person-title']/following-sibling::ul[1]/li"):
            nb_infos += 1
            #line = info.get().replace("\n", " ")
            line = html2text.html2text(info.get()).strip()
            line = re.sub("^\* *", "", line)

            # u"\u00A0" = Unicode Character 'NO-BREAK SPACE'
            # Voir https://www.fileformat.info/info/unicode/char/a0/index.htm
            line = line.replace(u"\u00A0", " ")  # avant toute chose !
            line = re.sub(" * ", " ", line) # suppression espaces multiples
            texte_infos = texte_infos + "- " + line + '\n'

            logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : info = '{line}'")
            # on coupe la fin, inutile, de la forme ", à l'âge...", ", peut-être à l'âge...", ...
            line = re.sub(",[^,]* l'âge .*", "", line)
            words = line.split()
            premier_mot = words[0]
            event_date_and_place = re.sub("^[^ ]*", "", line) # on enlève le premier mot (mais on garde l'espace, au cas date vide (exemple : "Né - lieu")
            event_date = re.sub(" - .*", "", event_date_and_place)
            event_date = re.sub("^ *", "", event_date)
            event_date = re.sub("^le ", "", event_date)
            event_date = re.sub("^en ", "", event_date)
            event_place = None
            #if " - " in event_date_and_place:
            #    event_place = re.sub("^[^-]* - ", "", event_date_and_place) # attention : on peut avoir des "-" dans le lieu
            n = event_date_and_place.find(" - ")
            if n >= 0:
                event_place = event_date_and_place[n+3:]
            event_dict = {
                "Né": "Naissance",
                "Née": "Naissance",
                "Baptisé" : "Baptême",
                "Baptisée" : "Baptême",
                "Décédé": "Décès",
                "Décédée": "Décès",
                "Inhumé": "Inhumation",
                "Inhumée": "Inhumation",
            }
            try:
                event_name = event_dict[premier_mot]  # ok, ou exception "KeyError"
                # C'est un événement connu :
                logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : --> event_name2='{event_name}' event_date2='{event_date}' event_place2='{event_place}' ")
                person.set_event(name=event_name, date=event_date, place=event_place)
            except:
                # Ce n'est pas un événement connu : peut-être la profession ? (sur la dernière ligne)
                if profession == None:
                    profession = line
                else:
                    nb_errors_indiv += 1
                    self.logger.error(f"Is '{profession}' an event ? Please check !")
                    self.nb_todo += 1
                    texte_infos = texte_infos + f"@todo vérifier l'événement '{profession}'\n"
                    profession = line
                pass
        if profession is not None:
            person.set_event(name="Profession", notes=profession)

        # Extraction "sous-titre" ou titre_noblesse/note_titre_noblesse
        # Cette info est présente dans la balise "em" juste après div[@id='person-title']
        #
        # Méthode 1 pas assez robuste (la balise "em" peut être loin, notamment dans § Sources !) :
        # info = response.xpath("//div[@id='person-title']/following-sibling::em[1]")
        # Méthode 2 plus robuste : on prend le premier voisin, s'il est de type "em") :
        # info = response.xpath("//div[@id='person-title']/following-sibling::*[1][name()='em']")
        # Mais il ne faut pas prendre @class='sosa' (cas avec ref sosa)
        sous_titre = None
        titre_noblesse = None
        note_titre_noblesse = None

        #info = response.xpath("//div[@id='person-title']/following-sibling::*[1][name()='em' and not(@class='sosa')]")
        #info = response.xpath("//div[@id='person-title']/following-sibling::*[name()='em' and not(@class='sosa')][1]")
        info = response.xpath("//div[@id='person-title']/following-sibling::em[not(@class='sosa')][1]")
        if info:
            lien_hyper = info.xpath("a")
            if lien_hyper:
                titre_noblesse = lien_hyper.xpath("text()").get().strip()
                #texte = info.xpath("text()").get()
                texte = info.get()
                texte = texte.replace(u"\u00A0", " ")  # avant toute chose : remplacer espace son sécable par espace normal
                texte = texte.replace("\n", " ")
                texte = texte.strip()
                # le texte est de la forme : "<em> <a href="xxxxx">Titre de noblesse</a>(commentaire)</em>'
                texte = re.sub(".*</a> *", "", texte) # on enlève tout avant "</a>"
                texte = re.sub(" *</em>$", "", texte) # on enlève le "</em>" final
                texte = re.sub("^\(", "", texte) # on enlève l'éventuelle parenthèse de début
                texte = re.sub("\)$", "", texte) # on enlève l'éventuelle parenthèse de fin
                #logger.info( f"Generation {generation}, sosa {sosa} : {prenom} {nom} : NRa_titre_noblesse1      = '{titre_noblesse}'")
                #logger.info( f"Generation {generation}, sosa {sosa} : {prenom} {nom} : NRa_note_titre_noblesse1 = '{texte}'")
                self.nb_titres_noblesse += 1
                if texte != "":
                    note_titre_noblesse = texte
                    self.nb_notes_titres_noblesse += 1
                    texte_infos = texte_infos + f"- titre: {titre_noblesse} ({note_titre_noblesse})\n"
                else:
                    texte_infos = texte_infos + f"- titre: {titre_noblesse}\n"
                person.add_title(self.gedcomw_parser.get_root_element(), titre_noblesse, note_titre_noblesse)
                logger.info( f"Generation {generation}, sosa {sosa} : {prenom} {nom} : titre_noblesse = '{titre_noblesse}' ({note_titre_noblesse})")
            else:
                texte = info.xpath("text()").get()
                texte = texte.replace(u"\u00A0", " ")  # avant toute chose : remplacer espace son sécable par espace normal
                texte = texte.strip()
                if texte != "":
                    sous_titre = texte
                    self.nb_sous_titres += 1
                    logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : sous_titre='{sous_titre}'")
                    person.add_note(self.gedcomw_parser.get_root_element(), sous_titre)
        nb_notes_longues = 0
        nb_evenements=0
        for event in response.xpath("//h2[span='Événements ']/following-sibling::table[1]/tr"):
            nb_evenements += 1
            #tmp = event.xpath("td[2]").get()
            #tmp = html2text.html2text(tmp)
            #event_name_and_place = event.xpath("td[2]/span[@class='nnom']/text()").get().strip()
            event_name_and_place = html2text.html2text(event.xpath("td[2]/span[@class='nnom']").get())
            event_name_and_place = event_name_and_place.replace(u"\u00A0", " ")  # avant toute chose : remplacer espace son sécable par espace normal
            event_name_and_place = event_name_and_place.replace("\n", " ")
            event_name_and_place = event_name_and_place.replace("_", "")
            event_name_and_place = event_name_and_place.strip()
            # contient : Naissance Baptême Profession Domicile Diplôme Décès Inhumation "Contrat de mariage (avec xxx)" "Mariage (avec xxx)"
            # suivi éventuellement du lieu
            event_name = re.sub(" *- .*", "", event_name_and_place)  # suppression " - .*" final
            event_place = None
            if " - " in event_name_and_place:
                event_place = re.sub(".* *- *", "", event_name_and_place)
            logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : '{event_name_and_place}' --> event_name='{event_name}' event_place='{event_place}'")

            lines = event.xpath("td[2]/div[@class='nnotes']").get()
            #logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : lines notes = '{lines}'")
            event_notes = None
            if not lines is None:
                #event_notes = html2text.html2text(event_notes)
                event_notes = html2text.html2text(lines).strip()
                event_notes = re.sub(" *\n", "\n", event_notes) # suppression des espaces ajoutés en fin de lignes
                event_notes = self.post_trt_notes(event_notes)
                if len(event_notes) >= self.lg_min_notes_longues :
                    nb_notes_longues += 1
                logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : event_notes = '{event_notes}'")

            lines = event.xpath("td[2]/p").get()
            #logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : lines paragraphe  = '{lines}'")
            event_notes_complementaires = None # infos de type témoins, parrains, ...
            if not lines is None:
                #event_notes = html2text.html2text(event_notes)
                event_notes_complementaires = html2text.html2text(lines).strip()
                event_notes_complementaires = re.sub(" *\n", "\n", event_notes_complementaires) # suppression des espaces ajoutés en fin de lignes
                event_notes_complementaires = self.post_trt_notes(event_notes_complementaires)
                if len(event_notes_complementaires) >= self.lg_min_notes_longues :
                    nb_notes_longues += 1
                logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : event_notes_complementaires = '{event_notes_complementaires}'")

            # Concaténetion event_notes + event_notes_complementaires
            event_notes2 = ""
            if not event_notes is None:
                event_notes2 = event_notes
            if not event_notes_complementaires is None:
                if event_notes2 == "":
                    event_notes2 = event_notes_complementaires
                else:
                    event_notes2 = event_notes2 + "\n" + event_notes_complementaires

            # on remplace event_notes avec l'éventuelle concaténetion de event_notes + event_notes_complementaires
            if not event_notes2 == "":
                event_notes = event_notes2

            lines = event.xpath("td[2]/span[@class='ssource']").get()
            event_sources = None
            #logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : lines sources = '{lines}'")
            if not lines is None:
                #event_sources = html2text.html2text(tmp)
                event_sources = html2text.html2text(lines).strip()
                # Patch sources de type "Décès" : Geneanet "oublie" le retour chariot, remplacé par "\- "
                if event_name == "Décès" :
                    event_sources = event_sources.replace( "\\- ", "\n", 1)
                event_sources = re.sub(" *\n", "\n", event_sources) # suppression des espaces ajoutés en fin de lignes
                event_sources = re.sub("^Sources: *", "", event_sources) # texte "Sources: " en début de source
                logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : event_sources = '{event_sources}'")

            lines = event.xpath("td[2]/span[@class='ddate small-12 show-for-small-only']").get()
            event_date = None
            if not lines is None:
                event_date = html2text.html2text(lines).strip()
                event_date = re.sub(" *: *$", "", event_date) # suppression " :" final
                event_date = event_date.replace("\n", " ")  # certaines dates ont des retours chariot (avec "julien")
                event_date = re.sub("  *", " ", event_date) # suppression espaces multiples
                logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : event_date = '{event_date}'")

            # 02/09/23 : finalement, je garde tous les événements, y compris mariages / contrats de mariage
            # pour avoir les notes, parfois intéressantes.
            # Complément avril 25 : je signale ceux n'apportant ni note ni source
            if GeneanetSpider.is_mariage.match(event_name) or GeneanetSpider.is_contrat_de_mariage.match(event_name) :
                # Evénement de la forme "Mariage (avec <conjoint>) - <lieu>"
                #                    ou "Contrat de mariage (avec <conjoint>) - <lieu>"
                logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : événement de type mariage / contrat de mariage '{event_name}' : date='{event_date}', place='{event_place}', notes='{event_notes}', source='{event_sources}'")
                if event_notes is None and event_sources is None :
                    logger.info( f"Generation {generation}, sosa {sosa} : {prenom} {nom} : redondance probable événement de type mariage / contrat de mariage SANS note ou source '{event_name}' : date='{event_date}', place='{event_place}'")
                    event_notes = f"@todo événement de type mariage probablement redondant pour {prenom} {nom}"

            #    # on ignore les infos (normalement, on les a via la fiche enfant)
            #    self.nb_todo += 1
            #    texte_infos = texte_infos + f"@todo vérifier prise en compte événement '{event_name}' pour {prenom} {nom}\n"
            #else:
            person.set_event(name=event_name, date=event_date, place=event_place, notes=event_notes, source=event_sources)
            # @todo y a-t-il d'autres classes ? parsing à robustifier

        nb_sources = 0
        for source in response.xpath("//h2[span='Sources']/following-sibling::em/ul[1]/li"):
            nb_sources += 1
            #line = source.xpath("text()").get()
            line1 = source.extract()
            line = html2text.html2text(line1).strip()
            #line = source.xpath("text()").extract()
            #event_name = re.sub(" *: .*", "xxx", line)  # suppression après ":"
            event_name = line.split(":",1)[0]
            event_name = re.sub("^\* *", "", event_name)  # suppression début "* "
            #event_sources = re.sub("[^:]*:  *", "", line)  # suppression avant ":"
            event_sources = line.split(":",1)[1]
            event_sources = re.sub("^ *", "", event_sources)  # suppression début " "
            # Patch sources de type "Décès" : Geneanet "oublie" le retour chariot, remplacé par "\- "
            if event_name == "Décès":
                event_sources = event_sources.replace("\\- ", "\n", 1)
            event_sources = re.sub(" *\n", "\n", event_sources)  # suppression des espaces ajoutés en fin de lignes
            if event_sources == "":
                # on teste avant ménage post-traitement
                nb_errors_indiv += 1
                self.logger.error(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : source vide ! Vérifier le code...")
            event_sources = self.post_trt_sources(event_sources)

            # après ménage, la source peut devenir vide (cas généalogie https://gw.geneanet.org/boutch1?lang=fr&n=revest&oc=0&p=gregorio)
            if event_sources != "":
                logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : source = '{line}'")

                event_list = event_name.split(",")
                for event_name in event_list:
                    # Cas particulier : on peut avoir en fait plusieurs événements concernés :
                    # exemples réels : "Naissance, décès: AG13", "Naissance, union 1: AG13", "Personne, famille: a d bouche du rhone"
                    event_name = event_name.strip().capitalize()
                    if event_name == "Personne" :
                        # Cette source concerne la personne elle-même, et non pas un événement :
                        source_personne = event_sources
                        logger.info( f"Generation {generation}, sosa {sosa} : {prenom} {nom} : --> source_personne='{source_personne}'")
                    elif (event_name == "Union") or (event_name == "Famille") :
                        # Cette source concerne le mariage de la personne (autre événement de type mariage) :
                        # --> on mémorise pour le restaurer lors de la génération des familles :
                        source_mariage = event_sources
                        self.mariages_sources[true_http_url] = source_mariage
                        logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : --> mariages_sources[{true_http_url}]='{source_mariage}'")
                    else:
                        logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : --> source '{event_name}' = '{event_sources}'")
                        person.set_event(name=event_name, source=event_sources)

        nb_notes = 0
        # Attention : class='note_type' rencontré à la fois pour span="Notes"/"Notes", mais aussi class="htitle"/"Notes concernant l'union"
        # ==> on teste uniquement h3[@class='note_type' au lieu de :
        # for note in response.xpath("//h2[span='Notes']/following-sibling::h3[@class='note_type']"):
        for note in response.xpath("//h3[@class='note_type']"):
            nb_notes += 1
            note_type = note.xpath("text()").get().strip()
            #note_text = note.xpath("following-sibling::p/text()").get() # ne donne que la premère ligne
            note_text = html2text.html2text(note.xpath("following-sibling::p").get()).strip() # ok, mais des cas vides (notes "individuelles")
            if note_text == "":
                following_text = note.xpath("following-sibling::text()[1]") # des cas où le texte est juste après
                if following_text :
                    note_text = following_text.get().strip()
            # Cas Notes individuelles :
            if note_text == "":
                #note_text = html2text.html2text(note.xpath("following-sibling::div[@class='fiche-note-ind']").get()).strip() # plantage sur jeu de tests
                note_indiv = note.xpath("following-sibling::div[@class='fiche-note-ind']").get()
                if note_indiv:
                    note_text = html2text.html2text(note_indiv).strip()
            note_text = re.sub(" *\n", "\n", note_text)  # suppression des espaces ajoutés en fin de lignes
            if note_text == "":
                # on teste avant ménage post-traitement
                nb_errors_indiv += 1
                self.logger.error(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : note {nb_notes} (type '{note_type}') vide ! Vérifier le code...")
            else :
                note_text = self.post_trt_notes(note_text)

            # après ménage, la note peut devenir vide (cas généalogie https://gw.geneanet.org/boutch1?lang=fr&n=revest&oc=0&p=gregorio)
            if note_text != "":
                if len(note_text) >= self.lg_min_notes_longues:
                    nb_notes_longues += 1
                logger.info( f"Generation {generation}, sosa {sosa} : {prenom} {nom} : note {nb_notes} (type '{note_type}') : note_text='{note_text}'")
                if note_type == "Notes individuelles":
                    person.add_note(self.gedcomw_parser.get_root_element(), note_text)
                elif (note_type == "Naissance") or (note_type == "Baptême") or (note_type == "Décès") or (note_type == "Inhumation") :
                    person.set_event(name=note_type, notes=note_text)
                elif GeneanetSpider.union_avec_regex.match(note_type):
                    self.nb_todo += 1
                    logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : note '{note_type}' à analyser : '{note_text}'")
                    texte_infos = texte_infos + f"@todo note '{note_type}' de {prenom} {nom} à analyser : '{note_text}'\n"
                else:
                    nb_errors_indiv += 1
                    self.logger.error(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : ERREUR : note_type('{note_type}') NON GERE. note_text='{note_text}'")
                    self.nb_todo += 1
                    texte_infos = texte_infos + f"@todo type note ('{note_type}') non géré pour {prenom} {nom}. Valeur='{note_text}'\n"

        nb_parents=0
        # Parents forme 1 ("<!-- Parents photo -->")
        presence_parents=""
        mariage_date = None
        mariage_place = None
        info_debug_csv = None
        parents_url= {}
        for parent in response.xpath("//div[@id='parents']/div/div/table/tr/td/ul/li") :
            nb_parents += 1
            url_parent = parent.xpath("a[count(img)=0]/@href").get() # ne pas prendre l'éventuel premier lien hypertexte (sosa) qui contient la balise img
            url_parent = response.urljoin(url_parent)
            presence_parents = "forme1" # forme 1
            # mars 2025 : beaucoup d'erreurs 403, dont certaines systématiques sur des url contenant "&iz=12"
            # (cas arbo https://gw.geneanet.org/jvo2506?lang=fr&n=van+brussel&oc=0&p=eduardus : https://gw.geneanet.org/jvo2506?lang=fr&iz=12&p=maria+joanna&n=pieters)
            # Etrangement, en supprimant ce champ "iz=", les erreurs disparaissent...
            url_parent = self.patch_url(url_parent)

            true_url_parent = self.url_to_true_http_url( true_http_url, url_parent)
            url_parent_to_scan = self.get_url_to_scan( true_url_parent)
            logger.info(f"URL parent {nb_parents} (forme 1) de {true_http_url} = {url_parent} (true='{true_url_parent}', to_scan='{url_parent_to_scan}'")
            parents_url[nb_parents]=true_url_parent

            self.set_parent_of( true_http_url, true_url_parent)
            #yield scrapy.Request(url_parent_to_scan, callback=self.parse, meta={'generation':generation,'sosa':sosa*2+nb_parents-1,'true_http_url':true_url_parent}, headers=self.HEADERS)
            self.add_link(url_parent_to_scan, meta={'generation':generation,'sosa':sosa*2+nb_parents-1})

        # Parents forme 2 ("<!-- Parents simple -->" ou "<!-- Parents complet -->")
        # Parents forme 2b ("<!-- Parents evolue -->") : il ne faut pas prendre le premier lien hypertexte (qui contient la balise img)
        if nb_parents == 0 :
            for parent in response.xpath("//h2[span='Parents']/following-sibling::ul[1]/li"):
                nb_parents += 1
                url_parent = parent.xpath("a[count(img)=0]/@href").get() # ne pas prendre l'éventuel premier lien hypertexte (sosa) qui contient la balise img
                url_parent = response.urljoin(url_parent)
                presence_parents = "forme2"  # forme 2
                url_parent = self.patch_url(url_parent) # suppression "&iz=xxx", "&pz=xxx", "&nz=xxx",... (voir explication plus haut)

                true_url_parent = self.url_to_true_http_url(true_http_url, url_parent)
                url_parent_to_scan = self.get_url_to_scan(true_url_parent)
                logger.info(f"URL parent {nb_parents} (forme 2) de {true_http_url} = {url_parent} (true='{true_url_parent}', to_scan='{url_parent_to_scan}'")
                parents_url[nb_parents] = true_url_parent

                # On essaye de voir s'il y a une ligne "Marié le ... avec" sur le premier parent :
                if nb_parents == 1:
                    lignes = parent.extract()
                    lignes = html2text.html2text(lignes).strip()
                    lignes = lignes.replace(u"\u00A0", " ")  # avant toute chose : remplacer espace son sécable par espace normal
                    lignes = lignes.replace("\n", " ") # sinon le match ne matche pas !!!!
                    lignes = lignes.replace("_", "")  # caractère de formatage introduit par html2text
                    info_debug_csv = lignes
                    lignes = lignes.replace("Contrat de mariage", "Marié") # on peut avoir "Contrat de mariage" au lieu de "Marié"
                    lignes = lignes.replace("Relation", "Marié") # peut-on aussi avoir "Relation" ici ? Dans le doute...
                    info_mariage = GeneanetSpider.ligne_mariage.match(lignes)
                    if info_mariage:
                        #logger.info( f"Match infos mariage sur parent {nb_parents} (forme 2) de {prenom} {nom} = '{lignes}'")
                        lignes = re.sub(".*Mariée* *", "", lignes)  # suppression avant "Marié"
                        lignes = re.sub(", *avec$", "", lignes)  # suppression ", avec" final
                        lignes = re.sub("avec$", "", lignes)  # suppression ", avec" final

                        if not lignes == "": # Lignes autres que seulement "Marié avec"
                            # Ici : séparateur date/lieu = virgule (et non pas tiret comme dans les infos générales)
                            mariage_date = re.sub(",.*$", "", lignes)
                            mariage_date = re.sub("^le ", "", mariage_date)
                            mariage_date = re.sub("^en ", "", mariage_date)
                            mariage_date = re.sub("^ *", "", mariage_date)
                            if "," in lignes:
                                mariage_place = re.sub("^[^,]*, *", "", lignes)
                            if mariage_date == "":
                                mariage_date = None
                            if mariage_place == "":
                                mariage_place = None
                            logger.info(f"Infos mariage sur parent {nb_parents} (forme 2) de {prenom} {nom} = date='{mariage_date}' place='{mariage_place}'")

                self.set_parent_of( true_http_url, true_url_parent)
                # yield scrapy.Request(url_parent_to_scan, callback=self.parse, meta={'generation':generation,'sosa':sosa*2+nb_parents-1,'true_http_url':true_url_parent}, headers=self.HEADERS)
                self.add_link(url_parent_to_scan, meta={'generation': generation, 'sosa': sosa*2+nb_parents-1})

        if nb_parents == 2 :
            key = self.key_union(parents_url[1], parents_url[2])
            if mariage_date:
                self.mariages_dates[key] = mariage_date
            else:
                mariage_date = ""
            if mariage_place:
                self.mariages_places[key] = mariage_place
            else:
                mariage_place = ""
            if not info_debug_csv:
                info_debug_csv = ""
            #mariage_place = mariage_place.encode(encoding="ascii", errors="replace") # robustesse écriture csv
            #info_debug_csv = info_debug_csv.encode(encoding="ascii", errors="replace") # robustesse écriture csv
            ligne = f"{pointer};{prenom};{nom};{true_http_url};§parents;{parents_url[1]};{parents_url[2]};\"{mariage_date}\";\"{mariage_place}\";\"{info_debug_csv}\";\n"
            self.csv_unions.write(ligne)


        elif nb_parents > 2 :
            nb_errors_indiv += 1
            self.logger.error(f"{nb_parents} parents for {prenom} {nom} ({true_http_url}) !")
            self.nb_todo += 1
            texte_infos = texte_infos + f"@todo à vérifier : {nb_parents} parents pour {prenom} {nom} !'\n"

        nb_unions = 0
        for union in response.xpath("//ul[@class='fiche_union']/li"):
            nb_unions += 1
            #line = source.xpath("text()").get()
            line1 = union.extract()
            line = html2text.html2text(line1).strip()
            #line = source.xpath("text()").extract()
            #event_name = re.sub(" *: .*", "xxx", line)  # suppression après ":"
            match_union = self.union_regex.match(line)
            if match_union:
                debut = match_union.groups(0)[0].strip()
                #nom_conjoint = match_union.groups(0)[1] KO si présence lien sosa
                #url_conjoint = match_union.groups(0)[2] # NON ! Ko si présence lien sosa
                url_conjoint = union.xpath("a[count(img)=0]/@href").get() # ne pas prendre l'éventuel premier lien hypertexte (sosa) qui contient la balise img
                url_conjoint = response.urljoin(url_conjoint)
                url_conjoint = self.url_to_true_http_url(true_http_url, url_conjoint)
                url_conjoint = self.patch_url(url_conjoint) # pour supprimer "&pz=xxxx&nz=xxxx" dans le cas sosa (important, car ne doit pas figurer dans la clé)
                nom_conjoint = union.xpath("a[count(img)=0]/text()").get() # ne pas prendre l'éventuel premier lien hypertexte (sosa) qui contient la balise img

                # La plupart du temps, on a forme "Marié ..." / "Mariée ...", sauf parfois :
                # "Relation" ou "Contrat de mariage"
                info = re.sub(".*Mariée* *", "", debut)  # suppression avant "Marié"
                info = info.replace("* Contrat de mariage", "")
                info = info.replace("* Relation", "")
                info = info.replace("_", "")  # caractère de formatage introduit par html2text
                info = re.sub("^\** *", "", info)

                mariage_date = re.sub(",.*$", "", info)
                mariage_date = re.sub("^le ", "", mariage_date)
                mariage_date = re.sub("^en ", "", mariage_date)
                mariage_date = re.sub("^ *", "", mariage_date)
                mariage_place = None
                if "," in info:
                    mariage_place = re.sub("^[^,]*, *", "", info)
                if mariage_date == "":
                    mariage_date = None
                if mariage_place == "":
                    mariage_place = None

                logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : union {nb_unions} = debut='{debut}' nom_conjoint='{nom_conjoint}' url_conjoint='{url_conjoint}' ")
                if sexe == "M":
                    url_pere = true_http_url
                    url_mere = url_conjoint
                else:
                    url_pere = url_conjoint
                    url_mere = true_http_url
                key = self.key_union(url_pere, url_mere)
                if mariage_date:
                    self.mariages_dates[key] = mariage_date
                else:
                    mariage_date = ""
                if mariage_place:
                    self.mariages_places[key] = mariage_place
                else:
                    mariage_place = ""

                # Autres notes (certains cas, pas tous, de "Notes concernant l'union"
                # for note in response.xpath("//*[@name='note-wed-1']"):
                # for note in response.xpath("//p[a/@name='note-wed-1']"):
                # le seul cas rencontré est :
                # <p><a name="note-wed-1"></a>...&#34;laquelle SYBILLE a accusé ledit BAR de crime de rapt...&#34;</p>
                # Par robustesse, je prends tout ce qui a @name='note-wed-*' (pas seulement balise "a" dans balise "p") :
                for note in response.xpath(f"//*[*/@name='note-wed-{nb_unions}']"):
                    nb_notes += 1
                    note_text = html2text.html2text(note.get()).strip()
                    note_text = re.sub(" *\n", "\n", note_text)  # suppression des espaces ajoutés en fin de lignes
                    if note_text == "":
                        # des cas où le text est dans la balise <p> suivante :
                        note_text = note.xpath("following-sibling::p/text()").get().strip()
                        note_text = re.sub(" *\n", "\n", note_text)  # suppression des espaces ajoutés en fin de lignes
                    if note_text == "":
                        nb_errors_indiv += 1
                        self.logger.error(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : note union vide ! Vérifier le code...")
                    else:
                        note_text = self.post_trt_notes(note_text)
                        # après ménage, la note peut devenir vide (cas généalogie https://gw.geneanet.org/boutch1?lang=fr&n=revest&oc=0&p=gregorio)
                        if note_text != "":
                            if len(note_text) >= self.lg_min_notes_longues:
                                nb_notes_longues += 1
                            self.mariages_note_union[key] = note_text
                            logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : note union {nb_unions} : '{note_text}'")

                #mariage_place = mariage_place.encode(encoding="ascii", errors="replace") # robustesse écriture csv
                #debut = debut.encode(encoding="ascii", errors="replace") # robustesse écriture csv
                ligne = f"{pointer};{prenom};{nom};{true_http_url};union{nb_unions};{url_pere};{url_mere};\"{mariage_date}\";\"{mariage_place}\";\"{debut}\";\n"
                self.csv_unions.write(ligne)

            else:
                nb_errors_indiv += 1
                self.logger.error(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : union {nb_unions} NON DECODEE = '{line}'")
                self.nb_todo += 1
                texte_infos = texte_infos + f"@todo à vérifier : union {nb_unions} NON DECODEE pour {prenom} {nom} = '{line}'\n"

        nb_err_events = person.manage_events( root_element=self.gedcomw_parser.get_root_element(), csv_log=self.csv_events, url=true_http_url)
        if nb_err_events > 0:
            self.nb_todo += 1
            texte_infos = texte_infos + f"@todo vérifier les événements pour {prenom} {nom} ({nb_err_events} erreur(s) détectée(s))\n"
        nb_errors_indiv += nb_err_events
        # Pour debug / vérif exports précédents :
        multiple_events_count = person.get_multiple_events_count()
        if multiple_events_count > 0:
            self.multiple_events_count += multiple_events_count
            logger.info( f"Generation {generation}, sosa {sosa} : {prenom} {nom} : multiple_events_count={multiple_events_count}")

        if source_personne is not None:
            texte_infos = texte_infos + "Sources : " + source_personne

        # Détection encart "Anomalies détectées"
        #if response.xpath("//gw-individual-anomalies"):
        #if response.xpath("//script[contains(text(),'gntGeneweb.person.anomalies')]"):
        #if not response.xpath("//script[contains(text(),\"GeneanetKeys.add('gntGeneweb.person.anomalies', [])\")]"): # KO avril 2025
        # avril 2025 : avant, pour une personne sans anomalie on avait "GeneanetKeys.add('gntGeneweb.person.anomalies', []);"
        # maintenant : "GeneanetKeys.add('gntGeneweb.person.anomalies',
        # 		   JSON.parse('[]'.replace(/&lt;/..."
        if not response.xpath("//script[contains(text(),\"GeneanetKeys.add('gntGeneweb.person.anomalies'\") and contains(text(),\"JSON.parse('[]'\")]"):
            nb_errors_indiv += 1
            self.logger.info(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : Geneanet signale des anomalies sur {prenom} {nom}. Vérifier la source.")
            self.nb_todo += 1
            texte_infos = texte_infos + f"@todo Geneanet signale des anomalies sur {prenom} {nom}. Vérifier la source.\n"

        # Liste/contrôle des rubriques
        #for info in response.xpath("//h2[span/@class]/span[2]/text()"): # NON à cause § "Union(s), enfant(s)"... : extraire text() après for
        for info in response.xpath("//h2[span/@class]/span[2]"):
            titre = info.xpath("text()").get();
            titre = titre.replace(u"\u00A0", " ")  # avant toute chose : remplacer espace son sécable par espace normal
            titre = titre.replace("\n", " ")
            titre = re.sub( "  *", " ", titre)
            titre = titre.strip()
            logger.info( f"Generation {generation}, sosa {sosa} : {prenom} {nom} : rubrique='{titre}'")
            if titre not in GeneanetSpider.paragraphes_connus :
                nb_errors_indiv += 1
                self.logger.error(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : rubrique '{titre}' inconnue !")
                self.nb_todo += 1
                texte_infos = texte_infos + f"@todo à vérifier : rubrique '{titre}' inconnue pour {prenom} {nom}.\n"

        self.nb_errors += nb_errors_indiv
        texte_infos = texte_infos.strip()
        person.add_source( self.gedcomw_parser.get_root_element(), true_http_url, texte_infos)
        self.nb_notes_longues += nb_notes_longues

        if profession == None:
            profession = ""
        if mariage_date == None:
            mariage_date = ""
        if mariage_place == None:
            mariage_place = ""
        if sous_titre == None:
            sous_titre = ""
        if titre_noblesse == None:
            titre_noblesse = ""
        if note_titre_noblesse == None:
            note_titre_noblesse = ""

        ligne = f"{generation};{sosa};{pointer};{prenom};{nom};{sexe};{true_http_url};{nb_infos};{nb_evenements};{nb_sources};{nb_parents};{presence_parents};{mariage_date};\"{mariage_place}\";\"{profession}\";\"{sous_titre}\";\"{titre_noblesse}\";\"{note_titre_noblesse}\";{nb_notes};{nb_notes_longues};\"{texte_infos}\";{nb_errors_indiv};\n"
        self.csv.write(ligne)


    def manage_families(self):
        #print(self.parents_of)
        #for item in self.parents_of.keys() :
        unions_children = {} # pointers des enfants, key = <url_pere>;<url_mere>
        unions_husband = {} # urls des pères, key = <url_pere>;<url_mere>
        unions_wife = {} # urls des mères, key = <url_pere>;<url_mere>

        # Première boucle pour identifier les familles
        # (et traiter les cas de consanguinité : plusieurs enfants d'un même couple dans l'arbre généalogique)
        for item in self.parents_of.items() :
            child_url = item[0]
            true_url_pere = None
            true_url_mere = None
            for parent_url in item[1]:
                #print(f"child {child} : parent {parent}", flush=True)
                try:
                    sexe = self.sex_of[parent_url][0]
                except KeyError:
                    # robustesse si on n'a pas parcouru toutes les pages (cas blocage robot)
                    sexe = "?"
                    pass
                if sexe == "M" and ((true_url_pere == None) or (true_url_pere == parent_url)) :
                    true_url_pere = parent_url
                elif sexe == "F" and ((true_url_mere == None) or (true_url_mere == parent_url)) :
                    true_url_mere = parent_url
                else :
                    self.nb_errors += 1
                    self.logger.error(f"Problem with parents of '{child_url}' : actual husband='{true_url_pere}', actual wife='{true_url_mere}', new parent '{parent_url}' sex '{sexe}'.")

            if (true_url_pere != None) and (true_url_mere != None):
                key = self.key_union(true_url_pere, true_url_mere)
                child_pointer = self.pointer_of[child_url]
                if key not in unions_children:
                    unions_children[key] = [child_pointer]
                    unions_husband[key] = true_url_pere
                    unions_wife[key] = true_url_mere
                else:
                    self.nb_consanguinites += 1
                    logger.info(f"consanguinité #{self.nb_consanguinites} pour union '{key}'")
                    unions_children[key].append(child_pointer)
            else:
                self.nb_errors += 1
                self.logger.error(f"Parent(s) missing for '{child_url}' : husband='{true_url_pere}', wife='{true_url_mere}'.")

        # Deuxième boucle pour constituer les familles
        for item in unions_children.items() :
            key = item[0]
            true_url_pere = unions_husband[key]
            true_url_mere = unions_wife[key]
            children_pointers = item[1]

            self.nb_families += 1
            pointer_family = "@F%05d@" % (self.nb_families)
            husband_pointer = self.pointer_of[true_url_pere]
            wife_pointer = self.pointer_of[true_url_mere]

            nb_children = len(children_pointers)
            logger.info(f"Famille '{pointer_family}' : père='{true_url_pere}', mère='{true_url_mere}', {nb_children} enfant(s)")
            mariage_note = None
            if nb_children > 1 :
                mariage_note = f"{nb_children} enfants dans l'arbre généalogique"
                logger.info(f"{nb_children} enfants dans la famille '{pointer_family}' (père='{true_url_pere}', mère='{true_url_mere}')")

            key = self.key_union(true_url_pere, true_url_mere)
            mariage_date = None
            mariage_place = None
            mariage_source = None
            try:
                mariage_date = self.mariages_dates[key]
            except:
                pass
            try:
                mariage_place = self.mariages_places[key]
            except:
                pass
            try:
                mariage_note_union = self.mariages_note_union[key]
                if mariage_note == None:
                    mariage_note = mariage_note_union
                else :
                    mariage_note = f"{mariage_note}\n{mariage_note_union}"
            except:
                pass
            try:
                mariage_source = self.mariages_sources[true_url_pere] # normalement, on a la même chose avec true_url_mere
                if self.mariages_sources[true_url_pere] != self.mariages_sources[true_url_mere]:
                    self.nb_errors += 1
                    self.logger.error(f"Famille '{pointer_family}' : ERREUR mariages_sources[père]('{mariage_source}') différent de mariages_sources[mère]('{self.mariages_sources[true_url_mere]}')")
                else:
                    logger.info(f"Famille '{pointer_family}' : OK : mariages_sources[père]=mariages_sources[mère]='{mariage_source}'")

                logger.info(f"Famille '{pointer_family}' : mariages_sources[{true_http_url}]='{mariage_source}'")
            except:
                pass

            logger.info(f"Famille '{pointer_family}' : enfant='{child_url}', true_url_pere='{true_url_pere}', true_url_mere='{true_url_mere}' mariage_date='{mariage_date}' mariage_place='{mariage_place}' mariage_source='{mariage_source}'")
            self.gedcomw_parser.add_family( pointer_family, children_pointers, husband_pointer, wife_pointer, mariage_date, mariage_place, mariage_source, mariage_note)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        # câblage de la méthode spider_closed
        spider = super(GeneanetSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def close(self):
        super().close()
        self.manage_families()
        self.gedcomw_parser.get_root_element().add_end_of_file()

        self.logger.info(f"Spider '{self.name}' closed :", )
        self.logger.info(f"- nb_persons            = {self.nb_persons}")
        self.logger.info(f"- nb_alias              = {self.nb_alias}")
        self.logger.info(f"- nb_masked_persons     = {self.nb_masked_persons}")
        self.logger.info(f"- nb_families           = {self.nb_families}")
        self.logger.info(f"- {len(self.parents_of)} relations enfants / parents")
        self.logger.info(f"- nb_consanguinites     = {self.nb_consanguinites}")
        self.logger.info(f"- max_generations       = {self.max_generations}")
        self.logger.info(f"- nb_titres_noblesse    = {self.nb_titres_noblesse} (avec {self.nb_notes_titres_noblesse} notes(s))")
        self.logger.info(f"- nb_sous_titres        = {self.nb_sous_titres}")
        self.logger.info(f"- nb_notes_longues      = {self.nb_notes_longues}")
        self.logger.info(f"- multiple_events_count = {self.multiple_events_count}")
        self.logger.info(f"- nb_errors             = {self.nb_errors}")
        self.logger.info(f"- nb_todo               = {self.nb_todo}")
        self.logger.info(f"- nb_scanned_pages      = {self.nb_scanned_pages}")
        self.logger.info(f"- nb_cached_pages       = {self.nb_cached_pages}")

        self.csv.write(f"# {self.nb_persons} persons, {self.nb_families} families, {self.max_generations} generations, {self.nb_titres_noblesse} titres de noblesse\n")
        self.csv.write(f"# {self.nb_errors} errors, {self.nb_todo} todo\n")
        self.csv.close()
        self.csv_events.close()
        self.csv_unions.close()

        gedresultfilename = self.result_dir + "/" + self.gedcom_result_filename
        self.logger.info(f"Saving to '{gedresultfilename}'")
        gedresult = open( gedresultfilename, "wb")
        self.gedcomw_parser.nra_save_gedcom(gedresult)
        gedresult.close()

        # renommage log
        final_logname = self.result_dir + "/" + self.result_name + ".log"
        try:
            os.remove(final_logname)
        except OSError:
            pass
        print(f"Renaming '{tmplogfile.name}' to '{final_logname}'", flush=True)
        """Ferme les handlers et renomme le fichier temporaire."""
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        shutil.copyfile(tmplogfile.name, final_logname)
        try:
            os.remove(tmplogfile.name)
        except OSError:
            print(f"Can't remove '{tmplogfile.name}' !'", flush=True)
            pass


if __name__ == "__main__":
    #if len(sys.argv) != 2:
    #    print("Usage: python geneanet_spider.py <URL_DE_DEPART>")
    #    sys.exit(1)
    parser = argparse.ArgumentParser(description=GeneanetSpider.progname)
    parser.add_argument("url")  # positionnel
    parser.add_argument("--max_pages", type=int, default=11)
    parser.add_argument("--max_cloudflare_errors", type=int, default=10)
    parser.add_argument("--min_delay", type=float, default=0.6)
    parser.add_argument("--max_delay", type=float, default=2.1)
    parser.add_argument("--headless", action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()
    crawler = GeneanetSpider( max_pages=args.max_pages, max_cloudflare_errors=args.max_cloudflare_errors, min_delay=args.min_delay, max_delay=args.max_delay, headless=args.headless )
    crawler.start(args.url)
