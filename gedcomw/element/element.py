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

from sys import version_info
from gedcomw.helpers import deprecated
import gedcomw.tags
import logging


class Element(object):
    """GEDCOM element

    Each line in a GEDCOM file is an element with the format

    level [pointer] tag [value]

    where level and tag are required, and pointer and value are
    optional.  Elements are arranged hierarchically according to their
    level, and elements with a level of zero are at the top level.
    Elements with a level greater than zero are children of their
    parent.

    A pointer has the format @pname@, where pname is any sequence of
    characters and numbers.  The pointer identifies the object being
    pointed to, so that any pointer included as the value of any
    element points back to the original object.  For example, an
    element may have a FAMS tag whose value is @F1@, meaning that this
    element points to the family record in which the associated person
    is a spouse.  Likewise, an element with a tag of FAMC has a value
    that points to a family record in which the associated person is a
    child.

    See a GEDCOM file for examples of tags and their values.
    """

    logger = logging.getLogger(__name__)  # Logger NRa
    logger.setLevel(logging.INFO)
    # NRa 06/08/23 : je supprime le StreamHandler, qui provoque une double sortie sur la console
    ## create console handler and set level to debug
    #ch = logging.StreamHandler()
    #ch.setLevel(logging.DEBUG)
    ## create formatter
    #formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    ## add formatter to ch
    #ch.setFormatter(formatter)
    ## add ch to logger
    #logger.addHandler(ch)
    logger.debug(f"NRa init class {__name__} #############################")

    def __init__(self, level, pointer, tag, value, crlf="\n", multi_line=True):
        """Initialize an element

        You must include a level, a pointer, a tag, and a value.
        Normally initialized by the GEDCOM parser, not by a user.

        :type level: int
        :type pointer: str
        :type tag: str
        :type value: str
        :type crlf: str
        :type multi_line: bool
        """

        # basic element info
        self.__level = level
        self.__pointer = pointer
        self.__tag = tag
        self.__value = value
        self.__crlf = crlf
        self.__nbSources = 0 # NRa : utile pour root_element seulement a priori
        self.__nbNotes = 0 # NRa : utile pour root_element seulement a priori
        self.list_of_events = []  # NRa : liste des événements, utile pour IndividualElement seulement
        self.nb_multiple_events = 0 # NRa : pour stats/debug : nombre d'événemnts multiples

        # structuring
        self.__children = []
        self.__parent = None

        if multi_line:
            self.set_multi_line_value(value)

        self.logger.debug(f"NRa init instance {__name__} : level={level} pointer={pointer} tag={tag} value={value} multi_line={multi_line}")
        #self.logger.debug(f"NRa aaaaaaaaaa")

    def get_next_source_pointer(self): # NRa
        """
        :rtype: str
        """
        self.__nbSources += 1
        source_pointer = "@S%05d@" % (self.__nbSources)
        return source_pointer

    def get_next_note_pointer(self): # NRa
        """
        :rtype: str
        """
        self.__nbNotes += 1
        note_pointer = "@N%05d@" % (self.__nbNotes)
        return note_pointer

    def get_level(self):
        """Returns the level of this element from within the GEDCOM file
        :rtype: int
        """
        return self.__level

    def get_pointer(self):
        """Returns the pointer of this element from within the GEDCOM file
        :rtype: str
        """
        return self.__pointer

    def get_tag(self):
        """Returns the tag of this element from within the GEDCOM file
        :rtype: str
        """
        return self.__tag

    def get_value(self):
        """Return the value of this element from within the GEDCOM file
        :rtype: str
        """
        return self.__value

    def set_value(self, value):
        """Sets the value of this element
        :type value: str
        """
        self.__value = value

    def get_multi_line_value(self):
        """Returns the value of this element including concatenations or continuations
        :rtype: str
        """
        result = self.get_value()
        last_crlf = self.__crlf
        for element in self.get_child_elements():
            tag = element.get_tag()
            if tag == gedcomw.tags.GEDCOM_TAG_CONCATENATION:
                result += element.get_value()
                last_crlf = element.__crlf
            elif tag == gedcomw.tags.GEDCOM_TAG_CONTINUED:
                result += last_crlf + element.get_value()
                last_crlf = element.__crlf
        return result

    def __available_characters(self):
        """Get the number of available characters of the elements original string
        :rtype: int
        """
        element_characters = len(self.to_gedcom_string())
        return 0 if element_characters > 255 else 255 - element_characters

    def __line_length(self, line):
        """@TODO Write docs.
        :type line: str
        :rtype: int
        """
        total_characters = len(line)
        available_characters = self.__available_characters()
        if total_characters <= available_characters:
            return total_characters
        spaces = 0
        while spaces < available_characters and line[available_characters - spaces - 1] == ' ':
            spaces += 1
        if spaces == available_characters:
            return available_characters
        return available_characters - spaces

    def __set_bounded_value(self, value):
        """@TODO Write docs.
        :type value: str
        :rtype: int
        """
        line_length = self.__line_length(value)
        self.set_value(value[:line_length])
        return line_length

    def __add_bounded_child(self, tag, value):
        """@TODO Write docs.
        :type tag: str
        :type value: str
        :rtype: int
        """
        child = self.new_child_element(tag)
        return child.__set_bounded_value(value)

    def __add_concatenation(self, string):
        """@TODO Write docs.
        :rtype: str
        """
        index = 0
        size = len(string)
        while index < size:
            index += self.__add_bounded_child(gedcomw.tags.GEDCOM_TAG_CONCATENATION, string[index:])

    def set_multi_line_value(self, value):
        """Sets the value of this element, adding concatenation and continuation lines when necessary
        :type value: str
        """
        self.set_value('')
        self.get_child_elements()[:] = [child for child in self.get_child_elements() if
                                        child.get_tag() not in (gedcomw.tags.GEDCOM_TAG_CONCATENATION, gedcomw.tags.GEDCOM_TAG_CONTINUED)]

        lines = value.splitlines()
        if lines:
            line = lines.pop(0)
            n = self.__set_bounded_value(line)
            self.__add_concatenation(line[n:])

            for line in lines:
                n = self.__add_bounded_child(gedcomw.tags.GEDCOM_TAG_CONTINUED, line)
                self.__add_concatenation(line[n:])

    def get_child_elements(self):
        """Returns the direct child elements of this element
        :rtype: list of Element
        """
        return self.__children

    def new_child_element(self, tag, pointer="", value=""):
        """Creates and returns a new child element of this element

        :type tag: str
        :type pointer: str
        :type value: str
        :rtype: Element
        """
        from gedcomw.element.family import FamilyElement
        from gedcomw.element.file import FileElement
        from gedcomw.element.individual import IndividualElement
        from gedcomw.element.object import ObjectElement

        # Differentiate between the type of the new child element
        if tag == gedcomw.tags.GEDCOM_TAG_FAMILY:
            child_element = FamilyElement(self.get_level() + 1, pointer, tag, value, self.__crlf)
        elif tag == gedcomw.tags.GEDCOM_TAG_FILE:
            child_element = FileElement(self.get_level() + 1, pointer, tag, value, self.__crlf)
        elif tag == gedcomw.tags.GEDCOM_TAG_INDIVIDUAL:
            child_element = IndividualElement(self.get_level() + 1, pointer, tag, value, self.__crlf)
        elif tag == gedcomw.tags.GEDCOM_TAG_OBJECT:
            child_element = ObjectElement(self.get_level() + 1, pointer, tag, value, self.__crlf)
        else:
            child_element = Element(self.get_level() + 1, pointer, tag, value, self.__crlf)

        self.add_child_element(child_element)

        return child_element

    def add_child_element(self, element):
        """Adds a child element to this element

        :type element: Element
        """
        self.get_child_elements().append(element)
        element.set_parent_element(self)

        return element

    def get_parent_element(self):
        """Returns the parent element of this element
        :rtype: Element
        """
        return self.__parent

    def set_parent_element(self, element):
        """Adds a parent element to this element

        There's usually no need to call this method manually,
        `add_child_element()` calls it automatically.

        :type element: Element
        """
        self.__parent = element

    @deprecated
    def get_individual(self):
        """Returns this element and all of its sub-elements represented as a GEDCOM string
        ::deprecated:: As of version 1.0.0 use `to_gedcom_string()` method instead
        :rtype: str
        """
        return self.to_gedcom_string(True)

    def to_gedcom_string(self, recursive=False):
        """Formats this element and optionally all of its sub-elements into a GEDCOM string
        :type recursive: bool
        :rtype: str
        """
        self.logger.debug(f"NRa to_gedcom_string(recursive={recursive}) : level={self.get_level()} pointer={self.__pointer} tag={self.__tag} value='{self.__value}'")

        if self.get_level() < 0:
            return ''

        result = str(self.get_level())

        if self.get_pointer() != "":
            result += ' ' + self.get_pointer()

        result += ' ' + self.get_tag()

        if self.get_value() != "":
            result += ' ' + self.get_value()

        result += self.__crlf

        if recursive:
            for child_element in self.get_child_elements():
                result += child_element.to_gedcom_string(recursive) # NRa : ajout arg recursive

        return result

    def __str__(self):
        """:rtype: str"""
        if version_info[0] >= 3:
            return self.to_gedcom_string()

        return self.to_gedcom_string().encode('utf-8-sig')

    def add_source(self, root_element, title, text): # NRa
        """ Ajout d'une source
        :type rootelement: gedcomw.element.Element
        """
        source_pointer = root_element.get_next_source_pointer()

        element_source_ref = Element(self.get_level()+1, '', gedcomw.tags.GEDCOM_TAG_SOURCE, source_pointer, '\n', multi_line=False)
        self.add_child_element(element_source_ref)

        element_source = Element(0, source_pointer, gedcomw.tags.GEDCOM_TAG_SOURCE, '', '\n', multi_line=False)
        element_title = Element(1, '', gedcomw.tags.GEDCOM_TAG_TITLE, title, '\n', multi_line=False)
        element_source.add_child_element(element_title)
        if text is not None :
            element_text = Element(1, '', gedcomw.tags.GEDCOM_TAG_TEXT, text, '\n', multi_line=True)
            element_source.add_child_element(element_text)
        root_element.add_child_element(element_source)

    def add_note(self, root_element, note): # NRa
        """ Ajout d'une note
        :type rootelement: gedcomw.element.Element
        """
        note_pointer = root_element.get_next_note_pointer()

        element_note_ref = Element(self.get_level()+1, '', gedcomw.tags.GEDCOM_TAG_NOTE, note_pointer, '\n', multi_line=False)
        self.add_child_element(element_note_ref)

        element_note = Element(0, note_pointer, gedcomw.tags.GEDCOM_TAG_NOTE, note, '\n', multi_line=True)
        root_element.add_child_element(element_note)

    def add_end_of_file(self): # NRa
        """ Ajout du tag de fin de fichier
        :type rootelement: gedcomw.element.Element
        """
        element = Element(0, '', gedcomw.tags.GEDCOM_TAG_TRLR, '', '\n', multi_line=False)
        self.add_child_element(element)




