

class Event(object):
    def __init__(self, name, date=None, place=None, notes=None, source=None):
        """Initialize Event
        :type name: str
        :type date: str
        :type place: str
        :type notes: str
        :type source: str
        """
        self._name = name
        self._date = date
        self._place = place
        self._notes = notes
        self._source = source

    def update(self, date=None, place=None, notes=None, source=None):
        """Initialize Event
        :type date: str
        :type place: str
        :type notes: str
        :type source: str
        """
        if date is not None:
            self._date = date
        if place is not None:
            self._place = place
        if notes is not None:
            self._notes = notes
        if source is not None:
            self._source = source
