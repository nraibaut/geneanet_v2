#!/bin/bash

#scrapy crawl test_firefox_spider -a start_url="https://www.google.com/"
#scrapy crawl test_firefox_spider -a start_url="https://gw.geneanet.org/ariellebdx?lang=fr&n=dupont&oc=0&p=pierre&type=fiche"

export PYTHONPATH=$(pwd)/geneanet  # pourquoi ai-je besoin de ça ???!!!!

python geneanet/spiders/simple_parser.py "https://gw.geneanet.org/ariellebdx?lang=fr&n=dupont&oc=0&p=pierre&type=fiche"

