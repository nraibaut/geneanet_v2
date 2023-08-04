#import gedcomw
from gedcomw.parser import Parser
#import gedcomw.element
#from gedcomw.element.individual import IndividualElement



# logger.info(f"DEBUT LECTURE GED")
gedcomw_parser2 = Parser()
gedcomw_parser2.parse_file("tests/Test.ged", True)
gedresult = open("tests/Test.out.ged", "wb")

# logger.info(f"FIN LECTURE GED")
# logger.info(f"DEBUT DUMP GED")
gedcomw_parser2.print_gedcom()
gedcomw_parser2.nra_save_gedcom(gedresult)
# gedcomw_parser2.nra_print_gedcom()
gedresult.close()
# logger.info(f"FIN DUMP GED")
