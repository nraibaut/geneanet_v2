#!/bin/bash

function go1()
{
scrapy crawl geneanet -a url="https://gw.geneanet.org/nraibaut2?lang=fr&n=dupont&oc=0&p=gerard"
scrapy crawl geneanet -a url="https://gw.geneanet.org/virgile81?lang=fr&n=schembri&oc=0&p=emmanuele"
scrapy crawl geneanet -a url="https://gw.geneanet.org/evechevaleyre?lang=fr&n=brincat&oc=0&p=maria+anna"
scrapy crawl geneanet -a url="https://gw.geneanet.org/danielr13?lang=fr&n=nicolas&oc=0&p=etienne+henri"
scrapy crawl geneanet -a url="https://gw.geneanet.org/ozone13?lang=fr&n=ollier&oc=0&p=jeanne+marie"
scrapy crawl geneanet -a url="https://gw.geneanet.org/jpifieec92?lang=fr&n=nicolas&oc=1&p=etienne"
}
function go2()
{
scrapy crawl geneanet -a url="https://gw.geneanet.org/bigoudi2018?lang=fr&n=ginoux&oc=0&p=antoinette"
scrapy crawl geneanet -a url="https://gw.geneanet.org/pascallacroix93?lang=fr&n=guiot&oc=0&p=anne"
scrapy crawl geneanet -a url="https://gw.geneanet.org/bboluix1?lang=fr&n=michel&oc=0&p=andre+michel"
}
function go3()
{
scrapy crawl geneanet -a url="https://gw.geneanet.org/oollierbolvin?lang=fr&n=mauche&oc=0&p=marie+anne"
scrapy crawl geneanet -a url="https://gw.geneanet.org/oollierbolvin?lang=fr&n=nicolas&oc=0&p=marguerite"
# scrapy crawl geneanet -a url="https://gw.geneanet.org/oollierbolvin?lang=fr&n=mauche&oc=0&p=marie+anne"
# Marguerite NICOLAS est la fille de Jacques NICOLAS et Marie Anne MAUCHE (qui m'intéressent) :
scrapy crawl geneanet -a url="https://gw.geneanet.org/oollierbolvin?lang=fr&n=nicolas&oc=0&p=marguerite"
scrapy crawl geneanet -a url="https://gw.geneanet.org/dmdoyen?lang=fr&n=mauche&oc=1&p=marie+anne"
# autre Marie Anne Mauche (aussi dans mon arbre)
scrapy crawl geneanet -a url="https://gw.geneanet.org/fapoja?lang=fr&n=mauche&oc=0&p=marie+anne"
}

rm result/*.log result/*.csv result/*.ged tmp/*.tmp 2>/dev/null

go1
go2
#go3

rm tmp/*.tmp

echo "-------------------------------------------------------------------------------------------------------------------"
echo "Erreurs / problemes :"
grep Traceback result/*.log
egrep 'Traceback|ERROR' result/*.log
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Anomalies ged / csv :"
egrep ' None | None$|\?\?\?' result/*.ged
grep -c sosa_symbol result/*.csv | grep -v ':0$'
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Anomalies Geneanet :"
grep 'Anomalies détectées' result/*.log
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Consanguinité :"
grep "enfants dans la famille" result/*.log
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Todo :"
grep @todo result/*.ged | grep -v '_ancestris'
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Statistiques :"
grep 'INFO: - ' result/*.log
echo "-------------------------------------------------------------------------------------------------------------------"
