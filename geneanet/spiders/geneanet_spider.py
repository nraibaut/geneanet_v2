import scrapy
from scrapy import signals
import html2text
import logging
from scrapy.utils.log import configure_logging
import gedcomw
from gedcomw.parser import Parser
import gedcomw.element
from gedcomw.element.individual import IndividualElement

class GeneanetSpider(scrapy.Spider):
    name = "geneanet"
    nb_persons = 0
    nb_titres_noblesse = 0
    max_generations = 0
    nb_warnings = 0
    nb_errors = 0
    configure_logging(install_root_handler=False)

    # Path to your `.ged` file
    gedcom_file_path = 'scrapy.ged'

    # Initialize the parser
    gedcomw_parser = Parser()

    xxxstart_urls = [
        #"https://gw.geneanet.org/fbiet?lang=fr&n=rochet&p=didier&oc=0",
        #"https://gw.geneanet.org/fbiet?n=rochet&oc=10&p=francois",
        #"https://gw.geneanet.org/fbiet?n=rochet&p=didier&oc=0",
        "https://gw.geneanet.org/nraibaut2_w?lang=fr&n=dupont&oc=0&p=gerard",
    ]

    def start_requests(self):
        logfile = "scrapy2.log"

        urls = [
            #"https://gw.geneanet.org/fbiet?n=rochet&p=didier&oc=0",
            "https://gw.geneanet.org/nraibaut2_w?lang=fr&n=dupont&oc=0&p=gerard", # tests
            #"https://gw.geneanet.org/virgile81?lang=fr&n=schembri&oc=0&p=emmanuele", # Emmanuele Schembri
            #"https://gw.geneanet.org/evechevaleyre?lang=fr&n=brincat&oc=0&p=maria+anna", # Maria Anna Brincat
            #"https://gw.geneanet.org/danielr13?lang=fr&n=nicolas&oc=0&p=etienne+henri", # Etienne Henri NICOLAS
        ]
        #logging_to_file(logfile)

        #logging.basicConfig(
        #    filename=logfile,
        #    format='zz %(asctime)s %(levelname)s: %(message)s',
        #    level=logging.INFO
        #)
        self.log(f"start_requests")

        for url in urls:
            #logging_to_file(logfile)
            #self.log.LOG_FILE = logfile
            yield scrapy.Request(url=url, callback=self.parse, meta={'generation':0, 'sosa':1} )

    def parse(self, response):
        source = response.request.url
        generation = response.meta['generation'] + 1
        if generation > self.max_generations :
            self.max_generations = generation
        sosa = response.meta['sosa']
        self.nb_persons += 1

        #generation = 1
        #prenom = response.xpath("//div[@id='person-title']//div//h1//a//text()")[0].extract()
        #nom = response.xpath("//div[@id='person-title']//div//h1//a//text()")[1].extract()
        #prenom = response.xpath("//div[@id='person-title']//div//h1//a[1]//text()")[0].extract()
        #nom = response.xpath("//div[@id='person-title']//div//h1//a[2]//text()")[0].extract()
        prenom = response.xpath("//div[@id='person-title']//div//h1//a[1]//text()").get()
        nom = response.xpath("//div[@id='person-title']//div//h1//a[2]//text()").get()
        self.log(f"Generation {generation}, sosa {sosa} : '{prenom}' '{nom}' ({source})")
        #if self.nb_persons == 1 :
        #person = IndividualElement ()
        #element = IndividualElement(level, pointer, tag, value, crlf, multi_line=False)
        pointer = "@I%05d@" % (self.nb_persons)
        self.log(f"Avant création IndividualElement")
        person = IndividualElement(0, pointer, gedcomw.tags.GEDCOM_TAG_INDIVIDUAL, "value", '\n', multi_line=False)
        self.log(f"Après création IndividualElement")
        person.set_name(prenom,nom)
        self.gedcomw_parser.get_root_element().add_child_element(person)

        for info in response.xpath("//div[@id='person-title']/following-sibling::ul[1]/li/text()"):
            line = info.get()
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : info = '{line}'")

        for titre in response.xpath("//div[@id='person-title']/following-sibling::em[1]/a") :
            self.nb_titres_noblesse += 1
            titre_noblesse = titre.xpath("text()").get()
            # @todo extraire commentaire
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : titre_noblesse = '{titre_noblesse}'")

        for event in response.xpath("//h2[span='Événements ']/following-sibling::table[1]/tr"):
            #tmp = event.xpath("td[2]").get()
            #tmp = html2text.html2text(tmp)
            event_nom = event.xpath("td[2]/span[@class='nnom']/text()").get()
            lines = event.xpath("td[2]/div[@class='nnotes']").get()
            #self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : lines notes = '{lines}'")
            if lines is None:
                event_notes = None # @todo améliorer gestion des champs absents/vides
            else:
                event_notes = html2text.html2text(lines)
            #event_notes = html2text.html2text(event_notes)
            lines = event.xpath("td[2]/span[@class='ssource']").get()
            #self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : lines sources = '{lines}'")
            if lines is None:
                event_sources = None # @todo améliorer gestion des champs absents/vides
            else :
                event_sources = html2text.html2text(lines)
            #event_sources = html2text.html2text(tmp)
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : event_nom = '{event_nom}'")
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : event_notes = '{event_notes}'")
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : event_sources = '{event_sources}'")

        for source in response.xpath("//h2[span='Sources']/following-sibling::em/ul[1]/li"):
            #line = source.xpath("text()").get()
            line1 = source.extract()
            line = html2text.html2text(line1)
            #line = source.xpath("text()").extract()
            self.log(f"Generation {generation}, sosa {sosa} : {prenom} {nom} : source = '{line}'")

        idx=0
        # Parents forme 1 ("<!-- Parents photo -->")
        for parent in response.xpath("//div[@id='parents']/div/div/table/tr/td/ul/li") :
            idx += 1
            url_parent = parent.xpath("a/@href").get()
            url_parent = response.urljoin(url_parent)
            self.log(f"URL parent (forme 1) {idx} = {url_parent}")
            yield scrapy.Request(url_parent, callback=self.parse, meta={'generation':generation,'sosa':sosa*2+idx-1})

        # Parents forme 2 ("<!-- Parents simple -->")
        if idx == 0 :
            for parent in response.xpath("//h2[span='Parents']/following-sibling::ul[1]/li"):
                idx += 1
                url_parent = parent.xpath("a/@href").get()
                url_parent = response.urljoin(url_parent)
                self.log(f"URL parent (forme 2) {idx} = {url_parent}")
                yield scrapy.Request(url_parent, callback=self.parse, meta={'generation':generation,'sosa':sosa*2+idx-1})
        if idx > 2 :
            self.nb_errors += 1
            self.logger.error(f"{idx} parents for {prenom} {nom} ({source}) !")

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        # câblage de la méthode spider_closed
        spider = super(GeneanetSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        spider.logger.info("NRa Spider closed: %s", spider.name)
        spider.logger.info(f"nb_persons         = {self.nb_persons}")
        spider.logger.info(f"max_generations    = {self.max_generations}")
        spider.logger.info(f"nb_titres_noblesse = {self.nb_titres_noblesse}")
        spider.logger.info(f"nb_errors          = {self.nb_errors}")
        spider.logger.info(f"nb_warnings        = {self.nb_warnings}")
        self.gedcomw_parser.print_gedcom()
