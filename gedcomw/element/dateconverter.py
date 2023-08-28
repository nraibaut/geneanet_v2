# -*- coding: utf-8 -*-
#===============================================================================
# Format des dates :
# voir https://www.francogene.com/internet/gedcom.php#Formatdesdates
#
# Dans le vrai GEDCOM, une date comprend :
# 1/ un préfixe optionnel, choisi parmi: ABT (environ), BEF (avant), AFT (après).
#    Certains logiciels ont ajouté EST (estimé) ou WFT EST (estimé par World Family Tree)
# 2/ un quantième optionel
# 3/ un mois optionnel, en lettre choisi parmi: JAN, FEB, MAR, APR, MAY, JUN, JUL, AUG, SEP, OCT, NOV, DEC.
#    Certains logiciels francisés ont remplacé les mois par l'équivalent français (fév, avr, mai, aou, déc)
#    et ces dates peuvent être perdues quand elles sont relues par d'autres logiciels ou une configuration différente.
# 4/ une année optionnelle.  Il est impossible d'avoir seulement le quantième car il devient alors l'année.
# Vous remarquerez que tout est optionnel !  Il arrive en fait qu'une ligne DATE soit vide...
# Certains logiciels exigent que le format soit précis (2 chiffres pour le quantième par exemple).
#
#===============================================================================

import re

class DateConverter(object):
    # regexp calendrier républicain :
    # Certaines dates sont de la forme :
    # "le 12 thermidor an X  (31 juillet 1802)"
    # "le 20 floréal an VIII  (10 mai 1800)"
    # On va chercher à extraire la partie entre parenthèses
    repcal = re.compile("(.*) *\((.*)\).*")
    interval = re.compile("entre (.*) et (.*)")
    months = {
        "janvier"   : "JAN",
        "février"   : "FEB",
        "mars"      : "MAR",
        "avril"     : "APR",
        "mai"       : "MAY",
        "juin"      : "JUN",
        "juillet"   : "JUL",
        "août"      : "AUG",
        "septembre" : "SEP",
        "octobre"   : "OCT",
        "novembre"  : "NOV",
        "décembre"  : "DEC",
    }
    # Préfixes officiels : ABT(environ), BEF(avant), AFT(après).
    # Préfixes autres : EST (estimé) ou WFT EST (estimé par World Family Tree)
    # Dans Geneanet : "avant", "après", "vers", "peut-être" ("en" et "le" ignorés)
    # Dans Ancestris : "CAL" (calculée, en plus de EST), "INT" (interprêtée)
    # date estimée dans Ancestris affichée avec "peut-être" dans Geneanet
    prefixes = {
        "vers"      : "ABT",
        "avant"     : "BEF",
        "après"     : "AFT",
        "peut-être" : "EST",
    }
    def __init__(self, text):
        """Initialize Event
        :type text: str
        """
        self._orig = text
        self._qualificatif = "" # dans Geneanet
        self._prefix = ""
        self._republican_date = None
        text2 = text
        #for c in text2:
        #    print("c='" + c + "' ", ord(c))

        # u"\u00A0" = Unicode Character 'NO-BREAK SPACE'
        # Voir https://www.fileformat.info/info/unicode/char/a0/index.htm
        text2 = text2.replace(u"\u00A0", " ") # avant toute chose !

        text2 = text2.strip()
        text2 = text2.lower() # robustesse sur les mois

        isinterval = DateConverter.interval.match(text2)
        if isinterval:
            # C'est un intervalle "entre <date1> et <date2>"
            # ==> on extrait les 2 dates et on génère le format GEDCOM "BET ... AND ..."
            date1 = isinterval.groups(0)[0]
            date2 = isinterval.groups(0)[1]
            conv1 = DateConverter(date1)
            conv2 = DateConverter(date2)
            self._qualificatif = "entre"
            text2 = "BET " + conv1.to_gedcom_string() + " AND " + conv2.to_gedcom_string()
            self._text2 = text2.strip()

        else:
            # On enlève le "le " ou "en " parfois présent au début :
            text2 = re.sub("^le ", "", text2, 1)
            text2 = re.sub("^en ", "", text2, 1)

            # On supprime le jour de la semaine parfois présent à la fin :
            for jour in ("(lundi)", "(mardi)", "(mercredi)", "(jeudi)", "(vendredi)", "(samedi)", "(dimanche)"):
                text2 = text2.replace(jour, "", 1)

            # On regarde la présence éventuelle d'un qualificatif :
            words = text2.split()
            first_word = words[0]
            # for qualificatif in ("avant", "après", "vers", "peut-être"):
            try:
                prefix = DateConverter.prefixes[first_word]  # ok, ou exception "KeyError"
                self._qualificatif = first_word
                # on enlève d'abord le premier mot (Geneanet)
                text2 = re.sub("^" + first_word + " ", "", text2, 1)
                # On enlève le "le " ou "en " qui peut être après le qualificatif ("avant", "après", "vers", "peut-être") :
                text2 = re.sub("^le ", "", text2, 1)
                text2 = re.sub("^en ", "", text2, 1)
                # On remet le prefixe (gedcom)
                text2 = prefix + " " + text2
            except KeyError:
                pass

            isrepublicain = DateConverter.repcal.match(text2)
            if isrepublicain:
                self._republican_date = isrepublicain.groups(0)[0].strip()
                text2 = isrepublicain.groups(0)[1]

            text2 = re.sub("1er ", "1 ", text2, 1)

            for mois1 in DateConverter.months.keys():
                mois2 = DateConverter.months[mois1]
                # print(f"{mois1} --> {mois2}")
                text2 = text2.replace(mois1, mois2, 1)

            text2 = text2.upper()  # norme = majuscules

            self._text2 = text2.strip()

    def to_string(self):
        """Formats this element into a string
        :rtype: str
        """
        result = "date='" + self._text2 + "'"
        if self._qualificatif:
            result += " (" + self._qualificatif + ")"
        if self._republican_date:
            result += " (" + self._republican_date + ")"
        return result

    def to_gedcom_string(self):
        """ Get date in GEDCOM format
        :rtype: str
        """
        return self._text2

    def get_republican_date(self):
        """ Get republican date (or None)
        :rtype: str
        """
        return self._republican_date

    def __str__(self):
        """:rtype: str"""
        return self.to_gedcom_string()