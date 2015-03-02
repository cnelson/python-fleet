import json


class FleetObject(object):
    """A base class for representing the objects sent to, and returned by fleet

    Raises:
        AttributeError: You attempted to write to a read only properly / key

    This class stores a dict in self._data and provides access to it via keys and properties.

        >>> fo = FleetObject(data={'foo': 'bar'})
        >>> fo.foo
        'bar'
        >>> fo['foo']
        'bar'

    Once the data is set in the constructor, it cannot be overwritten without using methods to do so.

    >>> fo.foo = 'baz'
    AttributeError: FleetObject.foo can not be modified

    """
    def __init__(self, client=None, data=None):
        """
        Args:
            client (fleet.v1.Client, optional): The fleet client that retrieved this object
            data (dict, optional): Initialize this object with this data

        """

        self._update('_client', client)
        self._update('_data', data)

    def _update(self, name, value):
        """Uses the parent object's method to bypass our write protection and update ourselves

        Args:
            name (str): The attribute to set/update
            value: The value to assign to the attribute

        """
        return object.__setattr__(self, name, value)

    # Ensure we can be accessed via property or keys
    def __contains__(self, name):
        return name in self._data

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __getattr__(self, name):
        return self._data[name]

    # Ensure our properties cannot be written to directly
    def __setitem__(self, name, value):
        return self.__setattr__(name, value)

    def __setattr__(self, name, value):
        raise AttributeError('{0}.{1} can not be modified'.format(
            self.__class__.__name__,
            name
        ))

    def __str__(self):
        return json.dumps(self._data)

    def __repr__(self):
        return '<{0}: {1}>'.format(
            self.__class__.__name__,
            str(self)
        )

    def as_dict(self):
        """Return the internal data structure backing this object"""
        return dict(self._data)
