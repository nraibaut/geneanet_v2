#!/bin/bash

#scrapy crawl test_firefox_spider -a start_url="https://www.google.com/"
#scrapy crawl test_firefox_spider -a start_url="https://gw.geneanet.org/ariellebdx?lang=fr&n=dupont&oc=0&p=pierre&type=fiche"

export PYTHONPATH=$(pwd):$(pwd)/geneanet  # pourquoi ai-je besoin de ça ???!!!!
#echo "NETTOYAGE..."
#rm -f result/pages/*

python geneanet/spiders/geneanet_spider.py "https://gw.geneanet.org/ariellebdx?lang=fr&n=dupont&oc=0&p=pierre&type=fiche" # --max_pages 23 --no-headless

ls -al result/pages/*

