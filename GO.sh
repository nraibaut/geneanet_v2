#!/bin/bash

export PYTHONPATH=$(pwd):$(pwd)/geneanet  # pourquoi ai-je besoin de ça ???!!!!

function crawl()
{
  # DOWNLOAD_DELAY surchargeable (défaut = 2 secondes dans settings.py), applicable aux lectures http et fichiers en cache.
  # En plus de ce délai, une pause de "http_delay" (défaut = 2 secondes dans geneanet_spider.py) s'applique uniquement aux lectures http.
  #scrapy crawl geneanet -a url="$1" -s DOWNLOAD_DELAY=2
  #scrapy crawl geneanet -a url="$1"
  while true
  do
    python geneanet/spiders/geneanet_spider.py "$1" --max_cloudflare_errors 1 # --max_pages 23 --no-headless
    LOG=$(ls -t result/*.log | head -1)
    nb_to_scan="$(grep 'nb_scanned_pages *= [1-9]' "$LOG" 2>/dev/null | wc -l)"
    if [ "$nb_to_scan" == "0" ]; then
      break;
    else
      echo "============================================================================================"
      echo "Il reste encore des pages non lues en cache..."
      sleep 10
    fi
  done
}

# Entre parenthèses : valeurs précédentes, dec 2023
function go1()
{
  ##crawl "https://gw.geneanet.org/nraibaut2?lang=fr&n=dupont&oc=0&p=gerard"
  crawl "https://gw.geneanet.org/virgile81?lang=fr&n=schembri&oc=0&p=emmanuele" # 43 personnes, 9 générations
  crawl "https://gw.geneanet.org/danielr13?lang=fr&n=nicolas&oc=0&p=etienne+henri" # 386 (vs 374) personnes, 12 générations

  crawl "https://gw.geneanet.org/evechevaleyre?lang=fr&n=brincat&oc=0&p=maria+anna" # 35 personnes, 7 générations
  crawl "https://gw.geneanet.org/ozone13?lang=fr&n=ollier&oc=0&p=jeanne+marie" # 27 personnes, 8 générations

  crawl "https://gw.geneanet.org/jpifieec92?lang=fr&n=nicolas&oc=1&p=etienne" # 513 (vs 541) personnes, 39 générations
}
#  crawl "https://gw.geneanet.org/b277?lang=fr&n=nicolas&oc=3&p=etienne" #  personnes,  générations # beaucoup moins complet que jpifieec92

function go2()
{
  crawl "https://gw.geneanet.org/bigoudi2018?lang=fr&n=ginoux&oc=0&p=antoinette" # 13(vs 11) personnes, 5 générations
  crawl "https://gw.geneanet.org/pascallacroix93?lang=fr&n=guiot&oc=0&p=anne" # 7 personnes, 3 générations
  crawl "https://gw.geneanet.org/bboluix1?lang=fr&n=michel&oc=0&p=andre+michel" # 3 personnes, 2 générations
}

function go3()
{
  ### crawl "https://gw.geneanet.org/oollierbolvin?lang=fr&n=mauche&oc=0&p=marie+anne"
  # Marguerite NICOLAS est la fille de Jacques NICOLAS et Marie Anne MAUCHE (qui m'intéressent) :
  crawl "https://gw.geneanet.org/oollierbolvin?lang=fr&n=nicolas&oc=0&p=marguerite" # 647 personnes, 33 générations

  crawl "https://gw.geneanet.org/dmdoyen?lang=fr&n=mauche&oc=1&p=marie+anne" # 29 personnes, 8 générations

  # autre Marie Anne Mauche (aussi dans mon arbre)
  # complète quelques ancêtres en plus de danielr13
  crawl "https://gw.geneanet.org/fapoja?lang=fr&n=mauche&oc=0&p=marie+anne" # 45 personnes, 8 générations
}

function go4()
{
  crawl "https://gw.geneanet.org/boutch1?lang=fr&n=revest&oc=0&p=gregorio" # 634 (vs 641) personnes, 24 générations, beaucoup d'anomalies Geneanet

}
function go5()
{
###  crawl "https://gw.geneanet.org/jvo2506?lang=fr&iz=12&p=maria+joanna&n=pieters" # test KO
###  crawl "https://gw.geneanet.org/jvo2506?lang=fr&iz=12&p=laurent&n=van+brussel" # test KO
  crawl "https://gw.geneanet.org/jvo2506?lang=fr&n=van+brussel&oc=0&p=eduardus" # 55 personnes, 9 générations
  crawl "https://gw.geneanet.org/sh1?lang=fr&n=vermeulen&oc=0&p=anna+juliana" # 51 personnes, 7 générations
}
function go6()
{
  crawl "https://gw.geneanet.org/gaetanv1?lang=fr&n=gonzales&oc=0&p=ursule+esperance&type=fiche" # dec 2025

  # pour ascendance Balthazar TISSOT et Jeanne TREBILLON :
  crawl "https://gw.geneanet.org/dmdoyen?lang=fr&n=tissot&oc=0&p=magdelaine&type=fiche" # janv 2026
  crawl "https://gw.geneanet.org/pascallacroix93?lang=fr&n=tissot&oc=0&p=magdelaine&type=tree" # fev 2026
  
  crawl "https://gw.geneanet.org/dmdoyen?lang=fr&n=bechet&oc=0&p=pierre&type=fiche" # janv 2026
  crawl "https://gw.geneanet.org/oollierbolvin?lang=fr&n=ollier&oc=0&p=jean+joseph&type=fiche"
  # Françoise BURAVAND :
  crawl "https://gw.geneanet.org/sikerik?lang=fr&n=buravand&oc=0&p=francoise&type=fiche" # fev 2026
  crawl "https://gw.geneanet.org/blouche?lang=fr&n=buravand&oc=0&p=francoise&type=fiche" # fev 2026
  # pour ascendance Biélone DE GUERIN :
  crawl "https://gw.geneanet.org/jpifieec92?lang=fr&n=de+guerin&oc=0&p=bielonne+ou+bielone&type=fiche" # fev 2026
  crawl "https://gw.geneanet.org/jmayet73?lang=fr&n=de+guerin&oc=0&p=bielonne+ou+bielone&type=fiche" # fev 2026
  # pour ascendance Gillette JULLIAN : plusieurs sources contradictoires :
  crawl "https://gw.geneanet.org/jpifieec92?lang=fr&n=jullian&oc=0&p=gillette&type=fiche" # fev 2026
  crawl "https://gw.geneanet.org/bsacco2?lang=fr&n=jullian&oc=0&p=gilette&type=fiche" # fev 2026
}

function go_test()
{
  # arbre de test, avec juste 2 parents
  crawl "https://gw.geneanet.org/ariellebdx?lang=fr&n=dupont&oc=0&p=pierre&type=tree"
}
function go()
{
  go1
  go2
  go3
  go4
  go5
  go6
}

rm result/*.log result/*.csv result/*.ged tmp/*.tmp 2>/dev/null
mkdir -p "result/pages"

  #go
  #go1
  #go2
  #go3
  #go5
  go6
  #go_test

rm tmp/*.tmp

function go_logs()
{
echo "ANALYSE DES LOGS :"
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Plantages (Tracebacks) :"
egrep -H 'Traceback|During handling of the above exception, another exception occurred:' result/*.log
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Erreurs :"
#egrep -H 'Traceback|ERROR' result/*.log
grep -H 'ERROR' result/*.log | sed -e 's;@I[0-9]*@;@Ixxxxx@;g' -e 's; sosa [0-9]* ; sosa xxxxxx ;g' | sort
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Anomalies ged / csv :"
egrep -H ' None | None$|\?\?\?\?' result/*.ged | sed -e 's;@......@;@xxxxxx@;g' | sort
#grep -c sosa_symbol result/*.csv | grep -v ':0$'
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Anomalies Geneanet :"
grep -H 'Geneanet signale des anomalies' result/*.log | sed -e 's; sosa [0-9]* ; sosa xxxxxx ;g' | sort
#echo "-------------------------------------------------------------------------------------------------------------------"
#echo "Redondances événements de type mariage :"
#grep -H 'redondance probable événement de type mariage' result/*.log | sed -e 's; sosa [0-9]* ; sosa xxxxxx ;g' | sort
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Consanguinité :"
grep -H "enfants dans la famille" result/*.log | sed -e 's;@F[0-9]*@;@Fxxxxx@;g' | sort
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Todo :"
grep -H '@todo' result/*.ged | sed -e 's;@......@;@xxxxxx@;g' | sort | grep -v '_ancestris'
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Erreurs crawling 403 ou Cloudflare/crawling :"
egrep -H 'scrapy.core.engine.*Crawled.*403|httperror|HTTP status code is not handled or not allowed' result/*.log | egrep -v 'httperror/response_ignored_|log:..scrapy.spidermiddlewares.httperror.HttpErrorMiddleware.,'
egrep -Hi '.- erreurs.* : [1-9]' result/*.log
echo "Autres erreurs/warning crawling : ---------------------------------------------------------"
grep -H 'scrapy.core.engine.*DEBUG' result/*.log | egrep -v 'Crawled .403.|Crawled .200.'
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Statistiques :"
grep -H 'INFO: - ' result/*.log
echo "-------------------------------------------------------------------------------------------------------------------"
}

go_logs | tee result/synthese.log.txt

