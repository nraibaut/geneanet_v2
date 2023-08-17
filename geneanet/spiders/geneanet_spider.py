# -*- coding: utf-8 -*-
import os

import scrapy
from scrapy import signals
import html2text
import logging
from scrapy.utils.log import configure_logging
import gedcomw
from gedcomw.parser import Parser
import gedcomw.element
from gedcomw.element.individual import IndividualElement
from datetime import datetime
#import sys
import atexit
import shutil # pour copyfile final
import time # pour pause
import re
import tempfile

class GeneanetSpider(scrapy.Spider):
    name = "geneanet"
    progname = "GeneanetSpider"
    version = "0.1.0"
    team = "Nicolas Raibaut"
    address = "raibaut.nicolas@gmail.com" # "https://xxxxxx"
    result_dir = "result"
    result_name = "tbd.tmp" # sera connu plus tard
    nb_persons = 0
    nb_families = 0
    nb_titres_noblesse = 0
    max_generations = 0
    nb_warnings = 0
    nb_errors = 0
    nb_scanned_pages = 0
    nb_saved_pages = 0
    nb_cached_pages = 0
    list_tuples_child_of = []
    parents_of = {} # dictionnaire des parents de chaque individu (index = <pointer>)
    sex_of = {} # dictionnaire des sexes des parents de chaque individu (index = <pointer>)
    mariages_dates = {} # dictionnaire des dates de mariaqes (index = "<true_url_pere>;<true_url_mere>")
    mariages_places = {} # dictionnaire des lieux de mariages (index = "<true_url_pere>;<true_url_mere>")
    mariages_sources = {} # dictionnaire des sources de mariages (index = "<true_url_pere_ou_mere>")
    true_url_of = {} # dictionnaire des url (index = <pointer>)
    is_http_url = re.compile("^http[s]*:.*")
    #is_file_url = re.compile("^file:.*")
    is_contrat_de_mariage = re.compile("^Contrat de mariage \(avec .*\).*")
    ligne_mariage = re.compile(".*Mari.*avec.*")

    # Configuration fichier de sortie log :
    # problème : il faut le faire ici, sinon on rate le début du log (et ça ne marche pas dans start_requests)
    # mais on n'a pas encore l'url, à partir de laquelle on veut construire le nom du log.
    # Contournement : on écrit dans un log tmp et on renomme à la fin...
    tmplogfile = tempfile.NamedTemporaryFile(suffix=".log.tmp", prefix="scrapy.", dir="tmp").name
    configure_logging(install_root_handler=False)
    logging.basicConfig(
        filename=tmplogfile,
        # format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        format='[%(name)s] %(levelname)s: %(message)s',
        encoding='utf-8', # sinon les grep (de git bash) dans les logs ne fonctionnent pas sur les lignes accentuées !
        level=logging.DEBUG
    )
    logging.info(f"Starting {progname} {version}")

    # Initialize the parser
    gedcomw_parser = None

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
        return result

    def get_cache_files(self, http_url):
        """
        donne les noms des fichiers cache
        :param url:
        :return:
        """
        # url = une vraie URL http (https://...)
        # (pas "file:///compte?lang=fr&p=pierre&n=dupont"...)

        cache_base = self.result_dir + "/pages/" + self.url_to_filename(http_url)
        cache_html_page = cache_base + ".html"
        cache_url_file = cache_base + ".url.txt"

        return [cache_html_page, cache_url_file]

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
        Renvoie l'url à parser : celle en cache si on l'a déjà, sinon la vraie url
        :param url:
        :return:
        """
        # url = forcément une vraie URL http (https://...)

        result = true_http_url    # par défaut

        cache_files = self.get_cache_files(true_http_url)
        cache_html_page = cache_files[0]
        cache_url_file = cache_files[1]
        #self.log(f"Test pour true_http_url = '{true_http_url}' :")
        #self.log(f"os.path.isfile({cache_html_page}) = {os.path.isfile(cache_html_page)}")
        #self.log(f"os.path.isfile({cache_url_file}) = {os.path.isfile(cache_url_file)}")

        if os.path.isfile(cache_html_page) and os.path.isfile(cache_url_file):
            #result = "file:" + cache_html_page # KO... visiblement, il FAUT un chemin absolu !!!!
            #result = "file:D:/Users/Nicolas/Documents/Python/geneanet/" + cache_html_page
            result = "file:" + os.getcwd() + "/" + cache_html_page

        return result


    # On a déjà en cache la page et son url :
    def start_requests(self):
        result_name = self.url_to_filename(self.url)
        GeneanetSpider.result_name = result_name

        self.log("start_requests")
        self.log(f"URL = {self.url}")
        self.log(f"result_name = {result_name}")

        # Initialisation parser
        self.gedcomw_parser = Parser()

        GeneanetSpider.gedcom_result_filename = result_name + ".ged"
        self.log(f"gedcom_result_filename = {GeneanetSpider.gedcom_result_filename}")
        now = datetime.now()  # current date and time
        date = now.strftime("%d/%m/%Y à %H:%M")
        header_text = f"Cette généalogie a été créée par {self.progname} le {date} à partir de {self.url}"
        self.gedcomw_parser.nra_set_header(header_text, self.progname, self.version, self.progname,
                   self.team, self.address, GeneanetSpider.gedcom_result_filename)

        # Sorties CSV :
        csvfilename = self.result_dir + "/" + result_name + ".csv"
        self.log(f"csv persons = {csvfilename}")
        self.csv = open( csvfilename, "w") # encoding="utf-8" ?
        self.csv.write(f"generation;sosa;id;prenom;nom;sexe;source;nb_infos;nb_evenements;nb_sources;nb_parents;forme_parents;parents_mariage_date;parents_mariage_lieu;profession;sous_titre;titre_noblesse;note_titre_noblesse;nb_notes;infos;{date}\n")

        csvfilename = self.result_dir + "/" + result_name + ".events.csv"
        self.log(f"csv events = {csvfilename}")
        self.csv_events = open( csvfilename, "w") # encoding="utf-8" ?
        self.csv_events.write(f"id;prenom;nom;url;evenement;tag;date;gedcom_date;lieu;notes;source;notes_source;{date}\n")

        csvfilename = self.result_dir + "/" + result_name + ".unions.csv"
        self.log(f"csv unions = {csvfilename}")
        self.csv_unions = open( csvfilename, "w") # encoding="utf-8" ?
        self.csv_unions.write(f"id;prenom;nom;url;origine;url_pere;url_mere;date;lieu;{date}\n")

        true_url = self.url
        url_to_scan = self.get_url_to_scan(true_url)
        self.log(f"Root URL = {self.url} (true='{true_url}', to_scan='{url_to_scan}')")

        yield scrapy.Request(url=url_to_scan, callback=self.parse, meta={'generation':0, 'sosa':1, 'child_pointer':'', 'true_http_url':true_url} )

    def parse(self, response):
        url_source = response.request.url
        # soit une "vraie" url (https://...) soit un fichier (file://...)

        is_http_url = GeneanetSpider.is_http_url.match(url_source)

        if is_http_url :
            true_http_url = url_source
            cache_files = self.get_cache_files(true_http_url)
            cache_html_page = cache_files[0]
            cache_url_file = cache_files[1]
            self.nb_scanned_pages += 1
            if (not os.path.isfile(cache_html_page)) or (not os.path.isfile(cache_url_file)):
                # C'est une "vraie" url qu'on n'a pas encore en cache :
                self.log(f"Saving page {url_source} to '{cache_html_page}'")
                with open( cache_html_page, "wb") as f:
                    f.write(response.body)
                    f.close()
                self.log(f"Saving URL to '{cache_url_file}'")
                with open( cache_url_file, "w") as f:
                    f.writelines(url_source)
                    f.close()
                self.nb_saved_pages += 1
        else:
            self.nb_cached_pages += 1
            true_http_url = response.meta['true_http_url']

        generation = response.meta['generation'] + 1
        if generation > self.max_generations :
            self.max_generations = generation
        sosa = response.meta['sosa']
        child_pointer = response.meta['child_pointer']
        self.nb_persons += 1
        pointer = "@I%05d@" % (self.nb_persons)

        #generation = 1
        #prenom = response.xpath("//div[@id='person-title']//div//h1//a//text()")[0].extract()
        #nom = response.xpath("//div[@id='person-title']//div//h1//a//text()")[1].extract()
        #prenom = response.xpath("//div[@id='person-title']//div//h1//a[1]//text()")[0].extract()
        #nom = response.xpath("//div[@id='person-title']//div//h1//a[2]//text()")[0].extract()
        prenom = response.xpath("//div[@id='person-title']//div//h1//a[1]//text()").get()
        nom = response.xpath("//div[@id='person-title']//div//h1//a[2]//text()").get()
        sexe = response.xpath("//div[@id='person-title']//img//@title").get() # "H/F" en français, "M/F" en anglais
        if sexe == "H" :
            sexe = "M"
        if sexe not in ("M", "F") :
            self.nb_errors += 1
            self.logger.error(f"Sex ({sexe}) is not 'M' or 'F' for {prenom} {nom} ({true_http_url}) !")
        self.sex_of[pointer] = [sexe]
        # Tentative (KO) de pause pour limiter erreurs "Redirecting (302) to ..." / "Forbidden by robots.txt: ..."
        #pause = 0
        #if generation >= 3 :
        #    pause = 2 ** generation
        #    #pause = 1000
        #    pause = 0
        #    time.sleep(pause/1000)
        self.log(f"Generation {generation}, sosa {sosa}, id {pointer} : '{prenom}' '{nom}' ({sexe}) ({true_http_url})")
        self.true_url_of[pointer] = true_http_url # pour retrouver les infos sur les mariages

        if child_pointer != '' :
            self.log(f"'{prenom}' '{nom}' parent de {child_pointer}")
            self.list_tuples_child_of.append((child_pointer,pointer,sexe))
            #self.parents_of[child_pointer] = "aaa" # .append((pointer,sexe))
            if child_pointer not in self.parents_of :
                self.parents_of[child_pointer] = [pointer]
            else:
                self.parents_of[child_pointer].append(pointer)

        source_personne = None
        person = IndividualElement(0, pointer, gedcomw.tags.GEDCOM_TAG_INDIVIDUAL, "", '\n', multi_line=False)
        person.set_name(prenom,nom)
        person.set_sex(sexe)
        self.gedcomw_parser.get_root_element().add_child_element(person)

        nb_infos = 0
        texte_infos = ""
        profession = None
        for info in response.xpath("//div[@id='person-title']/following-sibling::ul[1]/li/text()"):
            nb_infos += 1
            line = info.get().replace("\n", " ")
            # u"\u00A0" = Unicode Character 'NO-BREAK SPACE'
            # Voir https://www.fileformat.info/info/unicode/char/a0/index.htm
            line = line.replace(u"\u00A0", " ")  # avant toute chose !
            line = re.sub(" * ", " ", line) # suppression espaces multiples
            texte_infos = texte_infos + "- " + line + '\n'

            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : info = '{line}'")
            # on coupe la fin, inutile, de la forme ", à l'âge...", ", peut-être à l'âge...", ...
            line = re.sub(",[^,]* l'âge .*", "", line)
            words = line.split()
            premier_mot = words[0]
            event_date_and_place = re.sub("^[^ ]*", "", line) # on enlève le premier mot (mais on garde l'espace, au cas date vide (exemple : "Né - lieu")
            event_date = re.sub(" - .*", "", event_date_and_place)
            event_date = re.sub("^le ", "", event_date)
            event_date = re.sub("^en ", "", event_date)
            event_date = re.sub("^ *", "", event_date)
            event_place = None
            if " - " in event_date_and_place:
                event_place = re.sub("^[^-]* - ", "", event_date_and_place) # attention : on peut avoir des "-" dans le lieu
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
                self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : --> event_name2='{event_name}' event_date2='{event_date}' event_place2='{event_place}' ")
                person.set_event(name=event_name, date=event_date, place=event_place)
            except:
                # Ce n'est pas un événement connu : peut-être la profession ? (sur la dernière ligne)
                if profession == None:
                    profession = line
                else:
                    self.nb_errors += 1
                    self.logger.error(f"Is '{profession}' an event ? Please check !")
                    profession = line
                pass

        # Extraction "sous-titre" ou titre_noblesse/note_titre_noblesse
        # Cette info est présente dans la balise "em" juste après div[@id='person-title']
        #
        # Méthode 1 pas assez robuste (la balise "em" peut être loin, notamment dans § Sources !) :
        # info = response.xpath("//div[@id='person-title']/following-sibling::em[1]")
        # Méthode 2 plus robuste : on prend le premier voisin, s'il est de type "em") :
        # info = response.xpath("//div[@id='person-title']/following-sibling::*[1][name()='em']")
        sous_titre = None
        titre_noblesse = None
        note_titre_noblesse = None

        info = response.xpath("//div[@id='person-title']/following-sibling::*[1][name()='em']")
        if info:
            lien_hyper = info.xpath("a")
            if lien_hyper:
                titre_noblesse = lien_hyper.xpath("text()").get().strip()
                #texte = info.xpath("text()").get()
                texte = info.get()
                texte = texte.replace(u"\u00A0", " ")  # avant toute chose : remplacer espace son sécable par espace normal
                texte = texte.replace(f"\n", " ")
                texte = texte.strip()
                texte = re.sub(".*\(", "", texte)
                texte = re.sub("\) *</em>$", "", texte)
                if texte != "":
                    note_titre_noblesse = texte
                texte_infos = texte_infos + f"- titre: {titre_noblesse} ({note_titre_noblesse})\n"
                person.add_title(self.gedcomw_parser.get_root_element(), titre_noblesse, note_titre_noblesse)
                self.log( f"Generation {generation}, sosa {sosa} : {prenom} {nom} : titre_noblesse = '{titre_noblesse}' ({note_titre_noblesse})")
            else:
                texte = info.xpath("text()").get()
                texte = texte.replace(u"\u00A0", " ")  # avant toute chose : remplacer espace son sécable par espace normal
                texte = texte.strip()
                if texte != "":
                    sous_titre = texte
                    self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : sous_titre='{sous_titre}'")
                    person.add_note(self.gedcomw_parser.get_root_element(), sous_titre)

        nb_evenements=0
        for event in response.xpath("//h2[span='Événements ']/following-sibling::table[1]/tr"):
            nb_evenements += 1
            #tmp = event.xpath("td[2]").get()
            #tmp = html2text.html2text(tmp)
            event_name_and_place = event.xpath("td[2]/span[@class='nnom']/text()").get().strip()
            # contient : Naissance Baptême Profession Domicile Diplôme Décès Inhumation "Contrat de mariage (avec xxx)"
            # suivi éventuellement du lieu
            event_name = re.sub(" *- .*", "", event_name_and_place)  # suppression " - .*" final
            event_place = None
            if " - " in event_name_and_place:
                event_place = re.sub(".* *- *", "", event_name_and_place)
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : '{event_name_and_place}' --> event_name='{event_name}' event_place='{event_place}'")

            lines = event.xpath("td[2]/div[@class='nnotes']").get()
            #self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : lines notes = '{lines}'")
            event_notes = None
            if not lines is None:
                #event_notes = html2text.html2text(event_notes)
                event_notes = html2text.html2text(lines).strip()
                self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : event_notes = '{event_notes}'")

            lines = event.xpath("td[2]/span[@class='ssource']").get()
            event_sources = None
            #self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : lines sources = '{lines}'")
            if not lines is None:
                #event_sources = html2text.html2text(tmp)
                event_sources = html2text.html2text(lines).strip()
                # Patch sources de type "Décès" : Geneanet "oublie" le retour chariot, remplacé par "\- "
                if event_name == "Décès" :
                    event_sources = event_sources.replace( "\\- ", "\n", 1)
                event_sources = re.sub(" *\n", "\n", event_sources) # suppression des espaces ajoutés en fin de lignes
                event_sources = re.sub("^Sources: *", "", event_sources) # texte "Sources: " en début de source
                self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : event_sources = '{event_sources}'")

            lines = event.xpath("td[2]/span[@class='ddate small-12 show-for-small-only']").get()
            event_ddate = None
            if not lines is None:
                event_date = html2text.html2text(lines).strip()
                event_date = re.sub(" *: *$", "", event_date) # suppression " :" final
                self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : event_date = '{event_date}'")

            if GeneanetSpider.is_contrat_de_mariage.match(event_name):
                # Evénement de la forme "Contrat de mariage (avec <conjoint>) - <lieu>"
                self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : événement contrat de mariage '{event_name}'")
                # on ignore les infos (normalement, on les a via la fiche enfant)
            else:
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
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : source = '{line}'")
            if event_name == "Personne" :
                # Cette source concerne la personne elle-même, et non pas un événement :
                source_personne = event_sources
                self.log( f"Generation {generation}, sosa {sosa} : {prenom} {nom} : --> source_personne='{source_personne}'")
            elif event_name == "Union" :
                # Cette source concerne concerne le mariage de la personne (autre événement de type mariage) :
                # --> on mémorise pour le restaurer lors de la génération des familles :
                source_mariage = event_sources
                self.mariages_sources[true_http_url] = source_mariage
                self.log( f"Generation {generation}, sosa {sosa} : {prenom} {nom} : --> mariages_sources[{true_http_url}]='{source_mariage}'")
            else:
                # Cas particulier : on peur avoir en fait plusieurs événements concernés :
                # exemples réels : "Naissance, décès: AG13", "Naissance, union 1: AG13"
                self.log( f"Generation {generation}, sosa {sosa} : {prenom} {nom} : --> event_name2='{event_name}' event_sources2='{event_sources}'")
                ev = event_name.split(",")
                for e in ev:
                    e = e.strip().capitalize()
                    self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : --> event_name3='{e}' event_sources2='{event_sources}'")
                    person.set_event(name=e, source=event_sources)

        nb_notes = 0
        for note in response.xpath("//h2[span='Notes']/following-sibling::h3[@class='note_type']"):
            nb_notes += 1
            note_type = note.xpath("text()").get().strip()
            #note_text = note.xpath("following-sibling::p/text()").get() # ne donne que la premère ligne
            note_text = html2text.html2text(note.xpath("following-sibling::p").get()).strip() # ok, mais des cas vides (notes "individuelles")
            # Cas Notes individuelles :
            if note_text == "":
                note_text = html2text.html2text(note.xpath("following-sibling::div[@class='fiche-note-ind']").get()).strip()
            #note_text = "?"
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : note {nb_notes} : note_type='{note_type}' note_text='{note_text}'")
            if note_type == "Notes individuelles":
                person.add_note(self.gedcomw_parser.get_root_element(), note_text)
            elif (note_type == "Naissance") or (note_type == "Décès"):
                person.set_event(name=note_type, notes=note_text)
            else:
                self.nb_errors += 1
                self.logger.error(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : ERREUR : note_type('{note_type}') NON GERE. note_text='{note_text}'")

        nb_parents=0
        # Parents forme 1 ("<!-- Parents photo -->")
        presence_parents=""
        mariage_date = None
        mariage_place = None
        parents_url= {}
        for parent in response.xpath("//div[@id='parents']/div/div/table/tr/td/ul/li") :
            nb_parents += 1
            url_parent = parent.xpath("a/@href").get()
            url_parent = response.urljoin(url_parent)
            presence_parents = "forme1" # forme 1

            true_url_parent = self.url_to_true_http_url( true_http_url, url_parent)
            url_parent_to_scan = self.get_url_to_scan( true_url_parent)
            self.log(f"URL parent {nb_parents} (forme 1) = {url_parent} (true='{true_url_parent}', to_scan='{url_parent_to_scan}'")
            parents_url[nb_parents]=true_url_parent

            yield scrapy.Request(url_parent_to_scan, callback=self.parse, meta={'generation':generation,'sosa':sosa*2+nb_parents-1,'child_pointer':pointer,'true_http_url':true_url_parent})

        # Parents forme 2 ("<!-- Parents simple -->" ou "<!-- Parents complet -->"
        if nb_parents == 0 :
            for parent in response.xpath("//h2[span='Parents']/following-sibling::ul[1]/li"):
                nb_parents += 1
                url_parent = parent.xpath("a/@href").get()
                url_parent = response.urljoin(url_parent)
                presence_parents = "forme2"  # forme 2

                true_url_parent = self.url_to_true_http_url(true_http_url, url_parent)
                url_parent_to_scan = self.get_url_to_scan(true_url_parent)
                self.log(f"URL parent {nb_parents} (forme 2) = {url_parent} (true='{true_url_parent}', to_scan='{url_parent_to_scan}'")
                parents_url[nb_parents] = true_url_parent

                # On essaye de voir s'il y a une ligne "Marié le ... avec" sur le premier parent :
                if nb_parents == 1:
                    lignes = parent.extract()
                    lignes = html2text.html2text(lignes).strip()
                    lignes = lignes.replace(u"\u00A0", " ")  # avant toute chose : remplacer espace son sécable par espace normal
                    lignes = lignes.replace(f"\n", " ") # sinon le match ne matche pas !!!!
                    lignes = lignes.replace(f"Contrat de mariage", "Marié") # on peut avoir "Contrat de mariage" au lieu de "Marié"
                    info_mariage = GeneanetSpider.ligne_mariage.match(lignes)
                    if info_mariage:
                        lignes = lignes.replace(f"_", "")  # caractère de formatage introduit par html2text
                        #self.log( f"Match infos mariage sur parent {nb_parents} (forme 2) de {prenom} {nom} = '{lignes}'")
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
                            self.log(f"Infos mariage sur parent {nb_parents} (forme 2) de {prenom} {nom} = date='{mariage_date}' place='{mariage_place}'")

                yield scrapy.Request(url_parent_to_scan, callback=self.parse, meta={'generation':generation,'sosa':sosa*2+nb_parents-1,'child_pointer':pointer,'true_http_url':true_url_parent})
        if nb_parents == 2 :
            key = parents_url[1] + ";" + parents_url[2]
            if mariage_date:
                self.mariages_dates[key] = mariage_date
            if mariage_place:
                self.mariages_places[key] = mariage_place
            #mariage_place = mariage_place.encode(encoding="ascii", errors="replace") # robustesse écriture csv
            self.csv_unions.write(f"{pointer};{prenom};{nom};{true_http_url};§parents;{parents_url[1]};{parents_url[2]};\"{mariage_date}\";\"{mariage_place}\";\n")


        elif nb_parents > 2 :
            self.nb_errors += 1
            self.logger.error(f"{nb_parents} parents for {prenom} {nom} ({true_http_url}) !")

        self.nb_errors += person.manage_events( root_element=self.gedcomw_parser.get_root_element(), csv_log=self.csv_events, url=true_http_url)
        if profession == None:
            profession = ""
        if source_personne is not None:
            texte_infos = texte_infos + "Sources : " + source_personne
        texte_infos = texte_infos.strip()
        person.add_source( self.gedcomw_parser.get_root_element(), true_http_url, texte_infos)

        # Liste/contrôle des rubriques
        #for info in response.xpath("//h2[span/@class]/span[2]/text()"): # NON à cause § "Union(s), enfant(s)"... : extraire text() après for
        for info in response.xpath("//h2[span/@class]/span[2]"):
            titre = info.xpath("text()").get();
            titre = titre.replace(u"\u00A0", " ")  # avant toute chose : remplacer espace son sécable par espace normal
            titre = titre.replace(f"\n", " ")
            titre = re.sub( "  *", " ", titre)
            titre = titre.strip()
            self.log( f"Generation {generation}, sosa {sosa} : {prenom} {nom} : rubrique='{titre}'")

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
        self.csv.write(f"{generation};{sosa};{pointer};{prenom};{nom};{sexe};{true_http_url};{nb_infos};{nb_evenements};{nb_sources};{nb_parents};{presence_parents};{mariage_date};{mariage_place};{profession};{sous_titre};{titre_noblesse};{note_titre_noblesse};{nb_notes};\"{texte_infos}\";\n")

    def manage_families(self):
        #print(self.list_tuples_child_of)
        #print(self.parents_of)
        #for item in self.parents_of.keys() :
        for item in self.parents_of.items() :
            child = item[0]
            husband = None
            wife = None
            for parent in item[1]:
                #print(f"child {child} : parent {parent}")
                sexe = self.sex_of[parent][0]
                if sexe == "M" and husband == None :
                    husband = parent
                elif sexe == "F" and wife == None :
                    wife = parent
                else :
                    self.nb_errors += 1
                    self.logger.error(f"Problem with parents of '{child}' : actual husband='{husband}', actual wife='{wife}', new parent '{parent}' sex '{sexe}'.")
            self.nb_families += 1
            pointer_family = "@F%05d@" % (self.nb_families)
            self.log(f"Famille '{pointer_family}' : enfant='{child}', père='{husband}', mère='{wife}'")
            try:
                true_url_pere = self.true_url_of[husband]
            except:
                pass
            try:
                true_url_mere = self.true_url_of[wife]
            except:
                pass
            key = true_url_pere + ";" + true_url_mere
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
                mariage_source = self.mariages_sources[true_url_pere] # normalement, on a la même chose avec true_url_mere
                if self.mariages_sources[true_url_pere] != self.mariages_sources[true_url_mere]:
                    self.nb_errors += 1
                    self.logger.error(f"Famille '{pointer_family}' : ERREUR mariages_sources[père]('{mariage_source}') différent de mariages_sources[mère]('{self.mariages_sources[true_url_mere]}')")
                else:
                    self.log(f"Famille '{pointer_family}' : OK : mariages_sources[père]=mariages_sources[mère]='{mariage_source}'")

                self.log(f"Famille '{pointer_family}' : mariages_sources[{true_http_url}]='{mariage_source}'")
            except:
                pass

            self.log(f"Famille '{pointer_family}' : enfant='{child}', true_url_pere='{true_url_pere}', true_url_mere='{true_url_mere}' mariage_date='{mariage_date}' mariage_place='{mariage_place}' mariage_place='{mariage_source}'")
            self.gedcomw_parser.add_family( pointer_family, child, husband, wife, mariage_date, mariage_place, mariage_source)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        # câblage de la méthode spider_closed
        spider = super(GeneanetSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        self.manage_families()
        self.gedcomw_parser.get_root_element().add_end_of_file()

        spider.logger.info(f"NRa Spider '{spider.name}' closed :", )
        spider.logger.info(f"- nb_persons         = {self.nb_persons}")
        spider.logger.info(f"- nb_families        = {self.nb_families}")
        spider.logger.info(f"- max_generations    = {self.max_generations}")
        spider.logger.info(f"- nb_titres_noblesse = {self.nb_titres_noblesse}")
        spider.logger.info(f"- nb_errors          = {self.nb_errors}")
        spider.logger.info(f"- nb_warnings        = {self.nb_warnings}")
        spider.logger.info(f"- nb_scanned_pages   = {self.nb_scanned_pages}")
        spider.logger.info(f"- nb_saved_pages     = {self.nb_saved_pages}")
        spider.logger.info(f"- nb_cached_pages    = {self.nb_cached_pages}")

        self.csv.write(f"# {self.nb_persons} persons, {self.nb_families} families, {self.max_generations} generations, {self.nb_titres_noblesse} titres de noblesse\n")
        self.csv.write(f"# {self.nb_errors} errors, {self.nb_warnings} warnings\n")
        self.csv.close()
        self.csv_events.close()
        self.csv_unions.close()

        gedresultfilename = self.result_dir + "/" + GeneanetSpider.gedcom_result_filename
        spider.logger.info(f"Saving to '{gedresultfilename}'")
        gedresult = open( gedresultfilename, "wb")
        self.gedcomw_parser.nra_save_gedcom(gedresult)
        gedresult.close()


def close_logger(logger):
    """Close all handlers on logger object."""
    if logger is None:
        return
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


@atexit.register
def goodbye():
    print('Leaving the Python sector.')
    #close_logger(logging)
    #configure_logging(install_root_handler=True)
    #logging.shutdown()
    #os.rename(GeneanetSpider.tmplogfile, final_logname) # KO : erreur "fichier utilisé par un autre processus"
    final_logname = GeneanetSpider.result_dir + "/" + GeneanetSpider.result_name + ".log"
    try:
        os.remove(final_logname)
    except OSError:
        pass
    print(f"Renaming '{GeneanetSpider.tmplogfile}' to '{final_logname}'")
    shutil.copyfile(GeneanetSpider.tmplogfile, final_logname)
    try:
        os.remove(GeneanetSpider.tmplogfile)
    except OSError:
        print(f"Can't remove '{GeneanetSpider.tmplogfile}' !'")
        pass

