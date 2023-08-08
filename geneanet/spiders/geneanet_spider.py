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

#tmplogfile = "tmp.log"

class GeneanetSpider(scrapy.Spider):
    name = "geneanet"
    progname = "GeneanetSpider"
    version = "0.1.0"
    team = "Nicolas Raibaut"
    address = "raibaut.nicolas@gmail.com" # "https://xxxxxx"
    result_dir = "result"
    result_name = "tbd" # sera connu plus tard
    nb_persons = 0
    nb_families = 0
    nb_titres_noblesse = 0
    max_generations = 0
    nb_warnings = 0
    nb_errors = 0
    list_tuples_child_of = []
    parents_of = {} # dictionnaire des parents de chaque individu
    sex_of = {} # dictionnaire des sexes des parents de chaque individu



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
        result = result.replace("https://", "")
        result = result.replace("/", ".")
        result = result.replace("&", ".")
        result = result.replace("?", ".")

        return result

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

        # Sortie CSV :
        csvfilename = self.result_dir + "/" + result_name + ".csv"
        self.log(f"csv result = {csvfilename}")
        self.csv = open( csvfilename, "w")
        self.csv.write(f"generation;sosa;id;prenom;nom;sexe;source;nb_infos;nb_evenements;nb_sources;nb_parents;forme_parents;nb_titres;{date}\n")

        yield scrapy.Request(url=self.url, callback=self.parse, meta={'generation':0, 'sosa':1, 'child_pointer':''} )

    def parse(self, response):
        url_source = response.request.url

        # Sauvegarde de la page
        page_filename = self.result_dir + "/pages/" + self.url_to_filename(url_source) + ".html"
        self.log(f"Saving page {url_source} to '{page_filename}'")
        with open( page_filename, "wb") as f:
            f.write(response.body)
            f.close()

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
            self.logger.error(f"Sex ({sexe}) is not 'M' or 'F' for {prenom} {nom} ({url_source}) !")
        self.sex_of[pointer] = [sexe]
        # Tentative (KO) de pause pour limiter erreurs "Redirecting (302) to ..." / "Forbidden by robots.txt: ..."
        pause = 0
        if generation >= 3 :
            pause = 2 ** generation
            #pause = 1000
            pause = 0
            time.sleep(pause/1000)
        self.log(f"Generation {generation}, sosa {sosa}, id {pointer} : '{prenom}' '{nom}' ({sexe}) ({url_source}) pause={pause}ms")

        if child_pointer != '' :
            self.log(f"'{prenom}' '{nom}' parent de {child_pointer}")
            self.list_tuples_child_of.append((child_pointer,pointer,sexe))
            #self.parents_of[child_pointer] = "aaa" # .append((pointer,sexe))
            if child_pointer not in self.parents_of :
                self.parents_of[child_pointer] = [pointer]
            else:
                self.parents_of[child_pointer].append(pointer)

        #self.log(f"Avant création IndividualElement")
        person = IndividualElement(0, pointer, gedcomw.tags.GEDCOM_TAG_INDIVIDUAL, "", '\n', multi_line=False)
        #self.log(f"Après création IndividualElement")
        person.set_name(prenom,nom)
        person.set_sex(sexe)
        self.gedcomw_parser.get_root_element().add_child_element(person)
        person.add_source( self.gedcomw_parser.get_root_element(), url_source, 'texte')

        nb_infos = 0
        for info in response.xpath("//div[@id='person-title']/following-sibling::ul[1]/li/text()"):
            nb_infos += 1
            line = info.get().replace("\n", " ")
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : info = '{line}'")
            line = re.sub(", à l'âge .*", "", line) # on coupe la fin, inutile
            premier_mot = re.sub(" .*", "", line)
            event_date_and_place = re.sub("^[^ ]* *", "", line)
            event_date = re.sub(" *- *.*", "", event_date_and_place)
            event_date = re.sub("^le ", "", event_date) # @todo NE FONCTIONNE PAS !
            event_place = None
            if " - " in event_date_and_place:
                event_place = re.sub(".* *- *", "", event_date_and_place)
            if premier_mot in "Né" "Née":
                event_name = "Naissance"
                self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : --> event_name2='{event_name}' event_date2='{event_date}' event_place2='{event_place}' ")
                person.set_event(name=event_name, date=event_date, place=event_place)
            elif premier_mot in "Décédé" "Décédée":
                event_name = "Décès"
                self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : --> event_name2='{event_name}' event_date2='{event_date}' event_place2='{event_place}' ")
                person.set_event(name=event_name, date=event_date, place=event_place)

        nb_titres = 0
        for titre in response.xpath("//div[@id='person-title']/following-sibling::em[1]/a") :
            nb_titres += 1
            self.nb_titres_noblesse += 1
            titre_noblesse = titre.xpath("text()").get().strip()
            # @todo extraire commentaire
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : titre_noblesse = '{titre_noblesse}'")

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
                self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : event_sources = '{event_sources}'")

            lines = event.xpath("td[2]/span[@class='ddate small-12 show-for-small-only']").get()
            event_ddate = None
            if not lines is None:
                event_date = html2text.html2text(lines).strip()
                event_date = re.sub(" *: *$", "", event_date) # suppression " :" final
                self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : event_date = '{event_date}'")

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
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : --> event_name2='{event_name}' event_sources2='{event_sources}'")
            person.set_event(name=event_name, source=event_sources)

        nb_parents=0
        # Parents forme 1 ("<!-- Parents photo -->")
        presence_parents=""
        for parent in response.xpath("//div[@id='parents']/div/div/table/tr/td/ul/li") :
            nb_parents += 1
            url_parent = parent.xpath("a/@href").get()
            url_parent = response.urljoin(url_parent)
            self.log(f"URL parent (forme 1) {nb_parents} = {url_parent}")
            presence_parents = "forme1" # forme 1
            yield scrapy.Request(url_parent, callback=self.parse, meta={'generation':generation,'sosa':sosa*2+nb_parents-1,'child_pointer':pointer})

        # Parents forme 2 ("<!-- Parents simple -->")
        if nb_parents == 0 :
            for parent in response.xpath("//h2[span='Parents']/following-sibling::ul[1]/li"):
                nb_parents += 1
                url_parent = parent.xpath("a/@href").get()
                url_parent = response.urljoin(url_parent)
                self.log(f"URL parent (forme 2) {nb_parents} = {url_parent}")
                presence_parents = "forme2"  # forme 2
                yield scrapy.Request(url_parent, callback=self.parse, meta={'generation':generation,'sosa':sosa*2+nb_parents-1,'child_pointer':pointer})
        if nb_parents > 2 :
            self.nb_errors += 1
            self.logger.error(f"{nb_parents} parents for {prenom} {nom} ({url_source}) !")

        person.manage_events()
        self.csv.write(f"{generation};{sosa};{pointer};{prenom};{nom};{sexe};{url_source};{nb_infos};{nb_evenements};{nb_sources};{nb_parents};{presence_parents};{nb_titres};\n")

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
            self.gedcomw_parser.add_family( pointer_family, child, husband, wife)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        # câblage de la méthode spider_closed
        spider = super(GeneanetSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        self.manage_families()

        spider.logger.info(f"NRa Spider '{spider.name}' closed :", )
        spider.logger.info(f"- nb_persons         = {self.nb_persons}")
        spider.logger.info(f"- nb_families        = {self.nb_families}")
        spider.logger.info(f"- max_generations    = {self.max_generations}")
        spider.logger.info(f"- nb_titres_noblesse = {self.nb_titres_noblesse}")
        spider.logger.info(f"- nb_errors          = {self.nb_errors}")
        spider.logger.info(f"- nb_warnings        = {self.nb_warnings}")

        self.csv.write(f"# {self.nb_persons} persons, {self.nb_families} families, {self.max_generations} generations, {self.nb_titres_noblesse} titres de noblesse\n")
        self.csv.write(f"# {self.nb_errors} errors, {self.nb_warnings} warnings\n")
        self.csv.close()

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

