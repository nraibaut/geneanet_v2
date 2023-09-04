#!/bin/bash

function go1()
{
scrapy crawl geneanet -a url="https://gw.geneanet.org/nraibaut2?lang=fr&n=dupont&oc=0&p=gerard"
scrapy crawl geneanet -a url="https://gw.geneanet.org/virgile81?lang=fr&n=schembri&oc=0&p=emmanuele" # 43 personnes, 9 générations
scrapy crawl geneanet -a url="https://gw.geneanet.org/danielr13?lang=fr&n=nicolas&oc=0&p=etienne+henri" # 374 personnes, 12 générations

scrapy crawl geneanet -a url="https://gw.geneanet.org/evechevaleyre?lang=fr&n=brincat&oc=0&p=maria+anna" # 35 personnes, 7 générations
scrapy crawl geneanet -a url="https://gw.geneanet.org/ozone13?lang=fr&n=ollier&oc=0&p=jeanne+marie" # 27 personnes, 8 générations

scrapy crawl geneanet -a url="https://gw.geneanet.org/jpifieec92?lang=fr&n=nicolas&oc=1&p=etienne" # 541 personnes, 39 générations
#scrapy crawl geneanet -a url="https://gw.geneanet.org/b277?lang=fr&n=nicolas&oc=3&p=etienne" #  personnes,  générations # beaucoup moins complet que jpifieec92
}
function go2()
{
scrapy crawl geneanet -a url="https://gw.geneanet.org/bigoudi2018?lang=fr&n=ginoux&oc=0&p=antoinette" # 11 personnes, 5 générations
scrapy crawl geneanet -a url="https://gw.geneanet.org/pascallacroix93?lang=fr&n=guiot&oc=0&p=anne" # 7 personnes, 3 générations
scrapy crawl geneanet -a url="https://gw.geneanet.org/bboluix1?lang=fr&n=michel&oc=0&p=andre+michel" # 3 personnes, 2 générations
}
function go3()
{
# scrapy crawl geneanet -a url="https://gw.geneanet.org/oollierbolvin?lang=fr&n=mauche&oc=0&p=marie+anne"
# Marguerite NICOLAS est la fille de Jacques NICOLAS et Marie Anne MAUCHE (qui m'intéressent) :
scrapy crawl geneanet -a url="https://gw.geneanet.org/oollierbolvin?lang=fr&n=nicolas&oc=0&p=marguerite" # 647 personnes, 33 générations

scrapy crawl geneanet -a url="https://gw.geneanet.org/dmdoyen?lang=fr&n=mauche&oc=1&p=marie+anne" # 29 personnes, 8 générations

# autre Marie Anne Mauche (aussi dans mon arbre)
scrapy crawl geneanet -a url="https://gw.geneanet.org/fapoja?lang=fr&n=mauche&oc=0&p=marie+anne" # 45 personnes, 8 générations
}
function go4()
{
scrapy crawl geneanet -a url="https://gw.geneanet.org/boutch1?lang=fr&n=revest&oc=0&p=gregorio" # 641 personnes, 24 générations
}
function go()
{
go1
go2
go3
go4
}

rm result/*.log result/*.csv result/*.ged tmp/*.tmp 2>/dev/null
#scrapy crawl geneanet -a url="https://gw.geneanet.org/boutch1?lang=fr&n=revest&oc=0&p=gregorio" # 641 personnes, 24 générations

go
#go1
#go2
#go3

rm tmp/*.tmp

function go_logs()
{
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Plantages (Tracebacks) :"
egrep -H 'Traceback|During handling of the above exception, another exception occurred:' result/*.log
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Erreurs :"
#egrep -H 'Traceback|ERROR' result/*.log
grep -H 'ERROR' result/*.log
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Anomalies ged / csv :"
egrep -H ' None | None$|\?\?\?\?' result/*.ged
grep -c sosa_symbol result/*.csv | grep -v ':0$'
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Anomalies Geneanet :"
grep -H 'Anomalies détectées' result/*.log
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Consanguinité :"
grep -H "enfants dans la famille" result/*.log
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Todo :"
grep -H '@todo' result/*.ged | grep -v '_ancestris'
echo "-------------------------------------------------------------------------------------------------------------------"
echo "Statistiques :"
grep -H 'INFO: - ' result/*.log
echo "-------------------------------------------------------------------------------------------------------------------"
}
go_logs | tee result/synthese.log.txt
