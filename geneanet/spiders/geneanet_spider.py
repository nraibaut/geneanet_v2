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
    #logging_to_file(logfile)
    #logfile = self.result_dir + "/" + result_name + ".log"
    tmplogfile = result_dir + "/scrapy.log.tmp"

    # Configuration fichier de sortie log :
    # problème : il faut le faire ici, sinon on rate le début du log (et ça ne marche pas dans start_requests)
    # mais on n'a pas encore l'url, à partir de laquelle on veut construire le nom du log.
    # Contournement : on écrit dans un log tmp et on renomme à la fin...
    try:
        os.remove(tmplogfile)
    except OSError:
        pass
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

    def start_requests(self):
        result_name = self.url
        result_name = result_name.replace("https://", "")
        result_name = result_name.replace("/", ".")
        result_name = result_name.replace("&", ".")
        result_name = result_name.replace("?", ".")
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
        self.csv.write("# " + header_text + "\n")

        yield scrapy.Request(url=self.url, callback=self.parse, meta={'generation':0, 'sosa':1, 'child_pointer':''} )

    def parse(self, response):
        source = response.request.url
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
            self.logger.error(f"Sex ({sexe}) is not 'M' or 'F' for {prenom} {nom} ({source}) !")
        self.sex_of[pointer] = [sexe]
        # Tentative (KO) de pause pour limiter erreurs "Redirecting (302) to ..." / "Forbidden by robots.txt: ..."
        pause = 0
        if generation >= 3 :
            pause = 2 ** generation
            #pause = 1000
            time.sleep(pause/1000)
        self.log(f"Generation {generation}, sosa {sosa}, id {pointer} : '{prenom}' '{nom}' ({sexe}) ({source}) pause={pause}ms")
        self.csv.write(f"{generation};{sosa};{pointer};{prenom};{nom};{sexe};{source};")

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
        person.add_source( self.gedcomw_parser.get_root_element(), source, 'texte')

        for info in response.xpath("//div[@id='person-title']/following-sibling::ul[1]/li/text()"):
            line = info.get().replace("\n", " ")
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : info = '{line}'")

        for titre in response.xpath("//div[@id='person-title']/following-sibling::em[1]/a") :
            self.nb_titres_noblesse += 1
            titre_noblesse = titre.xpath("text()").get().strip()
            # @todo extraire commentaire
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : titre_noblesse = '{titre_noblesse}'")

        for event in response.xpath("//h2[span='Événements ']/following-sibling::table[1]/tr"):
            #tmp = event.xpath("td[2]").get()
            #tmp = html2text.html2text(tmp)
            event_nom = event.xpath("td[2]/span[@class='nnom']/text()").get().strip()
            lines = event.xpath("td[2]/div[@class='nnotes']").get()
            #self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : lines notes = '{lines}'")
            if lines is None:
                event_notes = None # @todo améliorer gestion des champs absents/vides
            else:
                event_notes = html2text.html2text(lines).strip()
            #event_notes = html2text.html2text(event_notes)
            lines = event.xpath("td[2]/span[@class='ssource']").get()
            #self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : lines sources = '{lines}'")
            if lines is None:
                event_sources = None # @todo améliorer gestion des champs absents/vides
            else :
                event_sources = html2text.html2text(lines).strip()
            #event_sources = html2text.html2text(tmp)
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : event_nom = '{event_nom}'")
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : event_notes = '{event_notes}'")
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : event_sources = '{event_sources}'")

        for source in response.xpath("//h2[span='Sources']/following-sibling::em/ul[1]/li"):
            #line = source.xpath("text()").get()
            line1 = source.extract()
            line = html2text.html2text(line1).strip()
            #line = source.xpath("text()").extract()
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : source = '{line}'")

        idx=0
        # Parents forme 1 ("<!-- Parents photo -->")
        for parent in response.xpath("//div[@id='parents']/div/div/table/tr/td/ul/li") :
            idx += 1
            url_parent = parent.xpath("a/@href").get()
            url_parent = response.urljoin(url_parent)
            self.log(f"URL parent (forme 1) {idx} = {url_parent}")
            yield scrapy.Request(url_parent, callback=self.parse, meta={'generation':generation,'sosa':sosa*2+idx-1,'child_pointer':pointer})

        # Parents forme 2 ("<!-- Parents simple -->")
        if idx == 0 :
            for parent in response.xpath("//h2[span='Parents']/following-sibling::ul[1]/li"):
                idx += 1
                url_parent = parent.xpath("a/@href").get()
                url_parent = response.urljoin(url_parent)
                self.log(f"URL parent (forme 2) {idx} = {url_parent}")
                yield scrapy.Request(url_parent, callback=self.parse, meta={'generation':generation,'sosa':sosa*2+idx-1,'child_pointer':pointer})
        if idx > 2 :
            self.nb_errors += 1
            self.logger.error(f"{idx} parents for {prenom} {nom} ({source}) !")
        self.csv.write("\n")

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
    print(f"Renaming '{GeneanetSpider.tmplogfile}' to '{final_logname}'")
    shutil.copyfile(GeneanetSpider.tmplogfile, final_logname)

