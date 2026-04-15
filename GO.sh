#!/bin/bash

export PYTHONPATH=$(pwd):$(pwd)/geneanet  # pourquoi ai-je besoin de ça ???!!!!

COVERAGE=1

function crawl()
{
  LAST_RESULT=result/last.log
  while true
  do
    if [ "$COVERAGE" == "1" ]; then
      coverage run --append --source=geneanet/spiders geneanet/spiders/geneanet_spider.py "$1" 2>&1 | tee "$LAST_RESULT"
    else
      python geneanet/spiders/geneanet_spider.py "$1" --max_cloudflare_errors 1 2>&1 | tee "$LAST_RESULT" # --no-headless
    fi
    nb_scanned_pages="$(grep 'nb_scanned_pages *=' "$LAST_RESULT" | sed -e 's/.*= *//g' 2>/dev/null)"
    # nb_scanned_pages = 0 ou plus, voire "" si le programme s'est planté avant la fin
    if [ "$nb_scanned_pages" == "0" ]; then
      break;
    else
      echo "============================================================================================"
      echo "Il reste encore des pages non lues en cache..."
      sleep 10
    fi
  done
  rm -f "$LAST_RESULT"
}
function go0()
{
  crawl "https://gw.geneanet.org/nraibaut2?lang=fr&n=dupont&oc=0&p=gerard"
}

function go1()
{
  crawl "https://gw.geneanet.org/virgile81?lang=fr&n=schembri&oc=0&p=emmanuele" ## avril 2026: idem: 43 personnes, 9 générations (importé dec 2023 : 43 personnes)
  crawl "https://gw.geneanet.org/danielr13?lang=fr&n=nicolas&oc=0&p=etienne+henri" ## avril 2026: idem: 386 (vs 374 dec 2023) personnes, 12 générations (importé avril 2025 : 386 personnes)

  crawl "https://gw.geneanet.org/evechevaleyre?lang=fr&n=brincat&oc=0&p=maria+anna" # avril 2026: idem: 35 personnes, 7 générations
  crawl "https://gw.geneanet.org/ozone13?lang=fr&n=ollier&oc=0&p=jeanne+marie" ## avril 2026: idem: 27 personnes, 8 générations (importé avril 2025 : 27 personnes)

  crawl "https://gw.geneanet.org/jpifieec92?lang=fr&n=nicolas&oc=1&p=etienne" # avril 2026: idem: 513 (vs 541 dec 2023) personnes, 39 générations
}
#  crawl "https://gw.geneanet.org/b277?lang=fr&n=nicolas&oc=3&p=etienne" # beaucoup moins complet que jpifieec92

function go2()
{
  crawl "https://gw.geneanet.org/bigoudi2018?lang=fr&n=ginoux&oc=0&p=antoinette" # avril 2026: 26 personnes, 7 générations (avant: 13(vs 11 dec 2023) personnes, 5 générations)
  crawl "https://gw.geneanet.org/pascallacroix93?lang=fr&n=guiot&oc=0&p=anne" ## avril 2026: idem: 7 personnes, 3 générations (importé manuel février 2026 : complète danielr13 et dmdoyen)
  crawl "https://gw.geneanet.org/bboluix1?lang=fr&n=michel&oc=0&p=andre+michel" # avril 2026: idem: 3 personnes, 2 générations
}

function go3()
{
  ### crawl "https://gw.geneanet.org/oollierbolvin?lang=fr&n=mauche&oc=0&p=marie+anne"
  # Marguerite NICOLAS est la fille de Jacques NICOLAS et Marie Anne MAUCHE (qui m'intéressent) :
  crawl "https://gw.geneanet.org/oollierbolvin?lang=fr&n=nicolas&oc=0&p=marguerite" # avril 2026: 649 personnes, 33 générations (avant: 647 personnes, 33 générations)

  crawl "https://gw.geneanet.org/dmdoyen?lang=fr&n=mauche&oc=1&p=marie+anne" # avril 2026: 39 personnes, 8 générations (avant: 29 personnes, 8 générations)

  # Autre Marie Anne Mauche (aussi dans mon arbre)
  # complète quelques ancêtres en plus de danielr13
  crawl "https://gw.geneanet.org/fapoja?lang=fr&n=mauche&oc=0&p=marie+anne" # avril 2026: idem: 45 personnes, 8 générations
}

function go4()
{
  crawl "https://gw.geneanet.org/boutch1?lang=fr&n=revest&oc=0&p=gregorio" # avril 2026: 181 personnes, 13 générations, 4 anomalies; avant : 634 (vs 641 dec 2023) personnes, 24 générations, beaucoup d'anomalies Geneanet
}

function go5()
{
###  crawl "https://gw.geneanet.org/jvo2506?lang=fr&iz=12&p=maria+joanna&n=pieters" # test KO
###  crawl "https://gw.geneanet.org/jvo2506?lang=fr&iz=12&p=laurent&n=van+brussel" # test KO
  crawl "https://gw.geneanet.org/jvo2506?lang=fr&n=van+brussel&oc=0&p=eduardus" ## avril 2026: 61 personnes, 9 générations (avant: 55 personnes, 9 générations) (importé avril 2025 : 55 personnes)
  crawl "https://gw.geneanet.org/sh1?lang=fr&n=vermeulen&oc=0&p=anna+juliana" ## avril 2026: idem: 51 personnes, 7 générations (importé avril 2025 : 51 personnes)
}
function go6()
{
  crawl "https://gw.geneanet.org/gaetanv1?lang=fr&n=gonzales&oc=0&p=ursule+esperance&type=fiche" # dec 2025: 19 personnes, 6 générations

  # pour ascendance Balthazar TISSOT et Jeanne TREBILLON :
  crawl "https://gw.geneanet.org/dmdoyen?lang=fr&n=tissot&oc=0&p=magdelaine&type=fiche" # janv 2026: 19 personnes, 5 générations
  crawl "https://gw.geneanet.org/pascallacroix93?lang=fr&n=tissot&oc=0&p=magdelaine&type=tree" # fev 2026: 19 personnes, 5 générations. Semble copié sur dmdoyen et moins détaillé, mais quelques écarts à vérifier
  
  crawl "https://gw.geneanet.org/dmdoyen?lang=fr&n=bechet&oc=0&p=pierre&type=fiche" # janv 2026: 27 personnes, 11 générations
  crawl "https://gw.geneanet.org/oollierbolvin?lang=fr&n=ollier&oc=0&p=jean+joseph&type=fiche" # 39 personnes, 7 générations
  # Françoise BURAVAND :
  crawl "https://gw.geneanet.org/sikerik?lang=fr&n=buravand&oc=0&p=francoise&type=fiche" # fev 2026: 21 personnes, 6 générations
  crawl "https://gw.geneanet.org/blouche?lang=fr&n=buravand&oc=0&p=francoise&type=fiche" # fev 2026: 13 personnes, 6 générations
  # pour ascendance Biélone DE GUERIN :
  crawl "https://gw.geneanet.org/jpifieec92?lang=fr&n=de+guerin&oc=0&p=bielonne+ou+bielone&type=fiche" # fev 2026: 393 personnes, 33 générations
  crawl "https://gw.geneanet.org/jmayet73?lang=fr&n=de+guerin&oc=0&p=bielonne+ou+bielone&type=fiche" # fev 2026, s'appuie sur jpifieec92 : 51 personnes, 11 générations
  # pour ascendance Gillette JULLIAN : plusieurs sources contradictoires :
  crawl "https://gw.geneanet.org/jpifieec92?lang=fr&n=jullian&oc=0&p=gillette&type=fiche" # fev 2026: 11 personnes, 4 générations
  crawl "https://gw.geneanet.org/bsacco2?lang=fr&n=jullian&oc=0&p=gilette&type=fiche" # fev 2026: 3 personnes, 2 générations
}

function go_test()
{
  # arbre de test, avec juste 2 parents
  #crawl "https://gw.geneanet.org/ariellebdx?lang=fr&n=dupont&oc=0&p=pierre&type=tree"
  # test événements unions 'Famille 1' 'Famille 2' :
  #crawl "https://gw.geneanet.org/bsacco2?lang=fr&n=jullian&oc=0&p=gilette&type=fiche" # fev 2026: 3 personnes, 2 générations
  #crawl "https://gw.geneanet.org/jmayet73?lang=fr&n=de+guerin&oc=0&p=bielonne+ou+bielone&type=fiche" # fev 2026
  crawl "https://gw.geneanet.org/jmayet73?lang=fr&n=christolin&oc=0&p=magdeleine&type=fiche" # "Magdeleine CHRISTOLIN" = fille de "Bielonne Ou Biélone de GUÉRIN" (pour avoir 1 des unions de sa mère, et vérifier la source)
  # test passage par "Infos mariage sur parent"
  crawl "https://gw.geneanet.org/evechevaleyre?lang=fr&n=brincat&oc=0&p=maria+anna" # fev 2026: 35 personnes, 7 générations
}

function go()
{
  go0
  go1
  go2
  go3
  go4
  go5
  go6
}

rm result/*.log result/*.csv result/*.ged tmp/*.tmp 2>/dev/null
mkdir -p "result/pages"

if [ "$COVERAGE" == "1" ]; then
  rm .coverage 2>/dev/null
fi

  go
  #go1
  #go2
  #go3
  #go4
  #go5
  #go6
  #go_test

rm tmp/*.tmp 2>/dev/null

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
echo "Recherche réapparition de code mort :"
grep -H 'CODE_MORT' result/*.log
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Statistiques :"
grep -H 'INFO: - ' result/*.log
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Synthèses :"
grep -H 'Synthèse en 1 ligne :' result/*.log
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Contrôle présence cas particuliers "
for key in nb_alias nb_masked_persons nb_consanguinites nb_titres_noblesse nb_sous_titres nb_notes_longues nb_events nb_event_dates nb_event_places nb_event_notes nb_event_notes2 nb_event_sources multiple_events_count
do
  echo "###### $key :"
  grep " - $key "  result/*.log | grep -v "= 0"
done
echo "-------------------------------------------------------------------------------------------------------------------"
}

go_logs | tee result/synthese.log.txt

cat result/*.log > result/all.log.txt

if [ "$COVERAGE" == "1" ]; then
  echo "Génération rapport coverage"
  coverage report -m
  coverage html --include=geneanet/spiders/geneanet_spider.py
fi
