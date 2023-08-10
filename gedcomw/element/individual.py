# -*- coding: utf-8 -*-

# Python GEDCOM Parser
#
# Copyright (C) 2018 Damon Brodie (damon.brodie at gmail.com)
# Copyright (C) 2018-2019 Nicklas Reincke (contact at reynke.com)
# Copyright (C) 2016 Andreas Oberritter
# Copyright (C) 2012 Madeleine Price Ball
# Copyright (C) 2005 Daniel Zappala (zappala at cs.byu.edu)
# Copyright (C) 2005 Brigham Young University
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Further information about the license: http://www.gnu.org/licenses/gpl-2.0.html

import re as regex
from gedcomw.element.element import Element
from gedcomw.element.event import Event # NRa
from gedcomw.helpers import deprecated
import gedcomw.tags
from gedcomw.element.dateconverter import DateConverter


class NotAnActualIndividualError(Exception):
    pass


class IndividualElement(Element):
    __givenname = "?"
    __surname = "?"
    #====================================================================
    # Etiquettes événements :
    # voir https://www.francogene.com/internet/gedcom.php#indi
    # (voir aussi doc Ancestris et norme : https://docs.ancestris.org/books/mode-demploi/page/gedcom)
    # OCCU	Occupation de l'individu.
    # BIRT	Naissance de l'individu.  Voir les lignes génériques d'un événement.
    # CHR	Le fait de donner un nom à l'individu (christening).  Certains logiciels préfèrent BAPT pour baptême. Voir les lignes génériques d'un événement.
    # BAPT	Baptême d'un individu.  Voir les lignes génériques d'un événement.
    # DEAT	Décès d'un individu.  Voir les lignes génériques d'un événement.
    # BURI	Inhumation ou sépulture d'un individu.  Chez les catholiques, il s'agit en général de l'inscription du décès dans un registre lors de la sépulture.  Voir les lignes génériques d'un événement.
    # EVEN	Autre événement.  Dans certaines logiciels, il peut s'agir du baptême ou de la sépulture.  On trouve alors un mot clé indiquant le type d'événement.  Dans d'autres logiciels, il s'agit du numéro d'une fiche d'événement qui contient alors les détails sur cet événement. Voir les lignes génériques d'un événement.
    # Autres :
    # ADOP	Adoption
    # CENS	Recensement
    # CONF	Confirmation
    # CRIM	Crime
    # DONA	Donation
    # EDUC	Éducation
    # EMIG	Émigration, départ d'un endroit
    # EMPL	Emploi
    # FCOM	Première communion
    # FUNE	Funérailles
    # HIST	Historique, chronologie de l'individu
    # IMMI	Immigration, arrivée dans un endroit
    # LVG	Vivant (living)
    # NATU	Naturalisation
    # NOBL	Anoblissement
    # ONDO	Ondoiement
    # ORDN	Ordination, entrée en religion
    # PASL	Liste de passagers
    # PROB	Ouverture d'un testament (probate)
    # RELI	Religion pratiquée
    # RESI	Résidence
    # RETI	Retraite
    # RMRK	Remarque
    # TBS	Pierre tombale (tombstone)
    # WILL	Testament
    #
    # Absent doc, mais présent export Ancestris et géré par Geneanet :
    # TITL  Titre
    # GRAD  Diplôme
    #
    #====================================================================

    event_dict = {
        "Baptême" : "CHR", # Ancestris exporte les baptèmes avec "CHR" (et non pas "BAPT")
        "Contrat de mariage" : "???", # @todo à voir
        "Diplôme" : "GRAD",
        "Domicile" : "RESI",
        "Décès" : "DEAT",
        "Inhumation" : "BURI",
        "Naissance" : "BIRT",
        "Personne" : "Personne???", # @todo à voir = uniquement source sur la personne ?
        "Profession" : "OCCU",
        "Retraite" : "RETI",
        "Union" : "Union???", # @todo à voir = uniquement source sur le mariage ?
    }

    def set_name(self, givenname, surname): # NRa
        # givenname = prénom = GEDCOM_TAG_GIVEN_NAME = "GIVN"
        # surname = nom de famille = GEDCOM_TAG_SURNAME = "SURN"
        self.__givenname = givenname
        self.__surname = surname
        name = "%s /%s/" % (givenname, surname)
        pointer = ''
        self.logger.debug(f"NRa {__name__} : set_name : givenname={givenname} surname={surname} (name='{name}')")
        element_name = Element( self.get_level()+1, pointer, gedcomw.tags.GEDCOM_TAG_NAME, name, '\n', multi_line=False)
        self.add_child_element(element_name)
        element_givenname = Element( self.get_level()+2, pointer, gedcomw.tags.GEDCOM_TAG_GIVEN_NAME, givenname, '\n', multi_line=False)
        element_surname = Element( self.get_level()+2, pointer, gedcomw.tags.GEDCOM_TAG_SURNAME, surname, '\n', multi_line=False)
        element_name.add_child_element(element_givenname)
        element_name.add_child_element(element_surname)

    def set_sex(self, sex): # NRa
        # sex = GEDCOM_TAG_SEX = "SEX"
        pointer = ''
        self.logger.debug(f"NRa {__name__} : set_sex : sex={sex}")
        element = Element( self.get_level()+1, pointer, gedcomw.tags.GEDCOM_TAG_SEX, sex, '\n', multi_line=False)
        self.add_child_element(element)

    def set_event(self, name, date=None, place=None, notes=None, source=None): # NRa
        self.logger.debug(f"set_event : name='{name}', date='{date}', place='{place}', notes='{notes}', source='{source}'")
        if name not in self.list_of_events:
            self.logger.debug(f"set_event : nouvelle clé name='{name}'")
            #event = Event(name, date, place, notes, source)
            self.list_of_events[name]=Event(name=name, date=date, place=place, notes=notes, source=source)
        else:
            self.logger.debug(f"set_event : maj clé existante name='{name}'")
            self.list_of_events[name].update( date=date, place=place, notes=notes, source=source)

    def manage_events(self, root_element, csv_log=None, url=''): # NRa
        """ Gère les événements d'un individu.
        Cette méthode est appelée en fin de traitement d'un individu, après consolidation de tous les
        évènements (par appels successifs de set_event, pouvant potentiellement se recouvrir entre événements).
        :rtype: int (nombre d'erreurs)
        """
        nb_errors = 0

        for key, event in self.list_of_events.items():
            #self.logger.info(f"event : name='{event._name}', date='{event._date}', place='{event._place}', notes='{event._notes}', source='{event._source}'")
            self.logger.info(f"manage_events : {self.get_pointer()} '{self.__givenname}' '{self.__surname}' : name='{event._name}', date='{event._date}', place='{event._place}', notes='{event._notes}', source='{event._source}'")
            tag = "?"
            try:
                tag = IndividualElement.event_dict[event._name]  # ok, ou exception "KeyError"
            except:
                tag = event._name + "???"
                nb_errors += 1
                self.logger.error( f"manage_events : {self.get_pointer()} '{self.__givenname}' '{self.__surname}' : unknown event name : '{event._name}'")
                pass
            element_etiq = Element(self.get_level() + 1, '', tag, '', '\n', multi_line=False)
            self.add_child_element(element_etiq)
            # @todo tag TYP (cas GRAD (diplôme)) : voir si ça vaut le coup de l'extraire de la 1ère ligne des notes
            date = ""
            gedcom_date = ""
            place = ""
            notes = ""
            source = ""
            notes_on_source = ""
            if event._date is not None and event._date is not "" :
                date = event._date
                conv = DateConverter(event._date)
                gedcom_date = conv.to_gedcom_string()
                element_date = Element(self.get_level() + 2, '', gedcomw.tags.GEDCOM_TAG_DATE, gedcom_date, '\n', multi_line=False)
                self.add_child_element(element_date)
            if event._place is not None and event._place is not "":
                place = event._place
                element_place = Element(self.get_level() + 2, '', gedcomw.tags.GEDCOM_TAG_PLACE, place, '\n', multi_line=False)
                self.add_child_element(element_place)
            if event._notes is not None:
                notes = event._notes
                self.add_note(root_element, event._notes)
            if event._source is not None:
                source = event._source
                # la chaîne contient :
                # - en première ligne la source
                # - en lignes suivantes les notes sur la source
                lines = event._source.splitlines()
                source = lines[0]
                notes_on_source = '\n'.join(lines[1:])
                self.add_source(root_element, source, notes_on_source)

            if csv_log is not None:
                csv_log.write(f"{self.get_pointer()};{self.__givenname};{self.__surname};{url};{event._name};{tag};{date};{gedcom_date};{place};\"{notes}\";\"{source}\";\"{notes_on_source}\";\n")

        return nb_errors

    def is_individual(self):
        """Checks if this element is an actual individual
        :rtype: bool
        """
        return self.get_tag() == gedcomw.tags.GEDCOM_TAG_INDIVIDUAL

    def is_deceased(self):
        """Checks if this individual is deceased
        :rtype: bool
        """
        if not self.is_individual():
            return False

        for child in self.get_child_elements():
            if child.get_tag() == gedcomw.tags.GEDCOM_TAG_DEATH:
                return True

        return False

    def is_child(self):
        """Checks if this element is a child of a family
        :rtype: bool
        """
        if not self.is_individual():
            raise NotAnActualIndividualError(
                "Operation only valid for elements with %s tag" % gedcomw.tags.GEDCOM_TAG_INDIVIDUAL
            )

        found_child = False

        for child in self.get_child_elements():
            if child.get_tag() == gedcomw.tags.GEDCOM_TAG_FAMILY_CHILD:
                found_child = True

        return found_child

    def is_private(self):
        """Checks if this individual is marked private
        :rtype: bool
        """
        if not self.is_individual():
            return False

        for child in self.get_child_elements():
            if child.get_tag() == gedcomw.tags.GEDCOM_TAG_PRIVATE:
                private = child.get_value()
                if private == 'Y':
                    return True

        return False

    def get_name(self):
        """Returns an individual's names as a tuple: (`str` given_name, `str` surname)
        :rtype: tuple
        """
        given_name = ""
        surname = ""

        if not self.is_individual():
            return given_name, surname

        # Return the first gedcomw.tags.GEDCOM_TAG_NAME that is found.
        # Alternatively as soon as we have both the gedcomw.tags.GEDCOM_TAG_GIVEN_NAME and _SURNAME return those.
        found_given_name = False
        found_surname_name = False

        for child in self.get_child_elements():
            if child.get_tag() == gedcomw.tags.GEDCOM_TAG_NAME:
                # Some GEDCOM files don't use child tags but instead
                # place the name in the value of the NAME tag.
                if child.get_value() != "":
                    name = child.get_value().split('/')

                    if len(name) > 0:
                        given_name = name[0].strip()
                        if len(name) > 1:
                            surname = name[1].strip()

                    return given_name, surname

                for childOfChild in child.get_child_elements():

                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_GIVEN_NAME:
                        given_name = childOfChild.get_value()
                        found_given_name = True

                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_SURNAME:
                        surname = childOfChild.get_value()
                        found_surname_name = True

                if found_given_name and found_surname_name:
                    return given_name, surname

        # If we reach here we are probably returning empty strings
        return given_name, surname

    def surname_match(self, surname_to_match):
        """Matches a string with the surname of an individual
        :type surname_to_match: str
        :rtype: bool
        """
        (given_name, surname) = self.get_name()
        return regex.search(surname_to_match, surname, regex.IGNORECASE)

    @deprecated
    def given_match(self, name):
        """Matches a string with the given name of an individual
        ::deprecated:: As of version 1.0.0 use `given_name_match()` method instead
        :type name: str
        :rtype: bool
        """
        return self.given_name_match(name)

    def given_name_match(self, given_name_to_match):
        """Matches a string with the given name of an individual
        :type given_name_to_match: str
        :rtype: bool
        """
        (given_name, surname) = self.get_name()
        return regex.search(given_name_to_match, given_name, regex.IGNORECASE)

    def get_gender(self):
        """Returns the gender of a person in string format
        :rtype: str
        """
        gender = ""

        if not self.is_individual():
            return gender

        for child in self.get_child_elements():
            if child.get_tag() == gedcomw.tags.GEDCOM_TAG_SEX:
                gender = child.get_value()

        return gender

    def get_birth_data(self):
        """Returns the birth data of a person formatted as a tuple: (`str` date, `str` place, `list` sources)
        :rtype: tuple
        """
        date = ""
        place = ""
        sources = []

        if not self.is_individual():
            return date, place, sources

        for child in self.get_child_elements():
            if child.get_tag() == gedcomw.tags.GEDCOM_TAG_BIRTH:
                for childOfChild in child.get_child_elements():

                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_DATE:
                        date = childOfChild.get_value()

                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_PLACE:
                        place = childOfChild.get_value()

                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_SOURCE:
                        sources.append(childOfChild.get_value())

        return date, place, sources

    def get_birth_year(self):
        """Returns the birth year of a person in integer format
        :rtype: int
        """
        date = ""

        if not self.is_individual():
            return date

        for child in self.get_child_elements():
            if child.get_tag() == gedcomw.tags.GEDCOM_TAG_BIRTH:
                for childOfChild in child.get_child_elements():
                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_DATE:
                        date_split = childOfChild.get_value().split()
                        date = date_split[len(date_split) - 1]

        if date == "":
            return -1
        try:
            return int(date)
        except ValueError:
            return -1

    def get_death_data(self):
        """Returns the death data of a person formatted as a tuple: (`str` date, `str` place, `list` sources)
        :rtype: tuple
        """
        date = ""
        place = ""
        sources = []

        if not self.is_individual():
            return date, place

        for child in self.get_child_elements():
            if child.get_tag() == gedcomw.tags.GEDCOM_TAG_DEATH:
                for childOfChild in child.get_child_elements():
                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_DATE:
                        date = childOfChild.get_value()
                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_PLACE:
                        place = childOfChild.get_value()
                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_SOURCE:
                        sources.append(childOfChild.get_value())

        return date, place, sources

    def get_death_year(self):
        """Returns the death year of a person in integer format
        :rtype: int
        """
        date = ""

        if not self.is_individual():
            return date

        for child in self.get_child_elements():
            if child.get_tag() == gedcomw.tags.GEDCOM_TAG_DEATH:
                for childOfChild in child.get_child_elements():
                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_DATE:
                        date_split = childOfChild.get_value().split()
                        date = date_split[len(date_split) - 1]

        if date == "":
            return -1
        try:
            return int(date)
        except ValueError:
            return -1

    @deprecated
    def get_burial(self):
        """Returns the burial data of a person formatted as a tuple: (`str` date, `str´ place, `list` sources)
        ::deprecated:: As of version 1.0.0 use `get_burial_data()` method instead
        :rtype: tuple
        """
        self.get_burial_data()

    def get_burial_data(self):
        """Returns the burial data of a person formatted as a tuple: (`str` date, `str´ place, `list` sources)
        :rtype: tuple
        """
        date = ""
        place = ""
        sources = []

        if not self.is_individual():
            return date, place

        for child in self.get_child_elements():
            if child.get_tag() == gedcomw.tags.GEDCOM_TAG_BURIAL:
                for childOfChild in child.get_child_elements():

                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_DATE:
                        date = childOfChild.get_value()

                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_PLACE:
                        place = childOfChild.get_value()

                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_SOURCE:
                        sources.append(childOfChild.get_value())

        return date, place, sources

    @deprecated
    def get_census(self):
        """Returns a list of censuses of an individual formatted as tuples: (`str` date, `str´ place, `list` sources)
        ::deprecated:: As of version 1.0.0 use `get_census_data()` method instead
        :rtype: list of tuple
        """
        self.get_census_data()

    def get_census_data(self):
        """Returns a list of censuses of an individual formatted as tuples: (`str` date, `str´ place, `list` sources)
        :rtype: list of tuple
        """
        census = []

        if not self.is_individual():
            raise NotAnActualIndividualError(
                "Operation only valid for elements with %s tag" % gedcomw.tags.GEDCOM_TAG_INDIVIDUAL
            )

        for child in self.get_child_elements():
            if child.get_tag() == gedcomw.tags.GEDCOM_TAG_CENSUS:

                date = ''
                place = ''
                sources = []

                for childOfChild in child.get_child_elements():

                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_DATE:
                        date = childOfChild.get_value()

                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_PLACE:
                        place = childOfChild.get_value()

                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_SOURCE:
                        sources.append(childOfChild.get_value())

                census.append((date, place, sources))

        return census

    def get_last_change_date(self):
        """Returns the date of when the person data was last changed formatted as a string
        :rtype: str
        """
        date = ""

        if not self.is_individual():
            return date

        for child in self.get_child_elements():
            if child.get_tag() == gedcomw.tags.GEDCOM_TAG_CHANGE:
                for childOfChild in child.get_child_elements():
                    if childOfChild.get_tag() == gedcomw.tags.GEDCOM_TAG_DATE:
                        date = childOfChild.get_value()

        return date

    def get_occupation(self):
        """Returns the occupation of a person
        :rtype: str
        """
        occupation = ""

        if not self.is_individual():
            return occupation

        for child in self.get_child_elements():
            if child.get_tag() == gedcomw.tags.GEDCOM_TAG_OCCUPATION:
                occupation = child.get_value()

        return occupation

    def birth_year_match(self, year):
        """Returns `True` if the given year matches the birth year of this person
        :type year: int
        :rtype: bool
        """
        return self.get_birth_year() == year

    def birth_range_match(self, from_year, to_year):
        """Checks if the birth year of a person lies within the given range
        :type from_year: int
        :type to_year: int
        :rtype: bool
        """
        birth_year = self.get_birth_year()

        if from_year <= birth_year <= to_year:
            return True

        return False

    def death_year_match(self, year):
        """Returns `True` if the given year matches the death year of this person
        :type year: int
        :rtype: bool
        """
        return self.get_death_year() == year

    def death_range_match(self, from_year, to_year):
        """Checks if the death year of a person lies within the given range
        :type from_year: int
        :type to_year: int
        :rtype: bool
        """
        death_year = self.get_death_year()

        if from_year <= death_year <= to_year:
            return True

        return False

    def criteria_match(self, criteria):
        """Checks if this individual matches all of the given criteria

        `criteria` is a colon-separated list, where each item in the
        list has the form [name]=[value]. The following criteria are supported:

        surname=[name]
             Match a person with [name] in any part of the `surname`.
        given_name=[given_name]
             Match a person with [given_name] in any part of the given `given_name`.
        birth=[year]
             Match a person whose birth year is a four-digit [year].
        birth_range=[from_year-to_year]
             Match a person whose birth year is in the range of years from
             [from_year] to [to_year], including both [from_year] and [to_year].

        :type criteria: str
        :rtype: bool
        """

        # Check if criteria is a valid criteria and can be split by `:` and `=` characters
        try:
            for criterion in criteria.split(':'):
                criterion.split('=')
        except ValueError:
            return False

        match = True

        for criterion in criteria.split(':'):
            key, value = criterion.split('=')

            if key == "surname" and not self.surname_match(value):
                match = False
            elif key == "name" and not self.given_name_match(value):
                match = False
            elif key == "birth":

                try:
                    year = int(value)
                    if not self.birth_year_match(year):
                        match = False
                except ValueError:
                    match = False

            elif key == "birth_range":

                try:
                    from_year, to_year = value.split('-')
                    from_year = int(from_year)
                    to_year = int(to_year)
                    if not self.birth_range_match(from_year, to_year):
                        match = False
                except ValueError:
                    match = False

            elif key == "death":

                try:
                    year = int(value)
                    if not self.death_year_match(year):
                        match = False
                except ValueError:
                    match = False

            elif key == "death_range":

                try:
                    from_year, to_year = value.split('-')
                    from_year = int(from_year)
                    to_year = int(to_year)
                    if not self.death_range_match(from_year, to_year):
                        match = False
                except ValueError:
                    match = False

        return match
