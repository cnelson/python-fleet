import unittest

import uuid

from ..objects import Machine


class TestMachine(unittest.TestCase):
    """Basic tests for the Machine object.

    Fleet states .metadata should be a dict exposed, but the machine, but if the machine exposes no metadata
    Fleet returns _nothing_ instead of an empty dict for metadata

    To provide a consistent interface, the object will inject an empty dict if the response from the server
    doesn't contain one.

    That behaivor is what these tests intend to execute
    """

    def setUp(self):
        self._id = uuid.uuid4().hex

        self._ip = "198.51.100.23"

    def test_no_metadata(self):
        """Machine with no metadata has appropriate structure"""

        test_obj = {
            "id": self._id,
            "primaryIP": self._ip
        }

        m = Machine(data=test_obj)

        assert m.id == self._id
        assert m['id'] == self._id

        assert m.primaryIP == self._ip
        assert m['primaryIP'] == self._ip

        assert m.metadata == {}
        assert m['metadata'] == {}

    def test_blank_metadata(self):
        """Machine with empty metadata has appropriate structure"""

        test_obj = {
            "id": self._id,
            "primaryIP": self._ip,
            "metadata": {}
        }

        m = Machine(data=test_obj)

        assert m.id == self._id
        assert m['id'] == self._id

        assert m.primaryIP == self._ip
        assert m['primaryIP'] == self._ip

        assert m.metadata == {}
        assert m['metadata'] == {}

    def test_with_metadata(self):
        """Machine with metadata has appropriate structure"""

        test_obj = {
            "id": self._id,
            "primaryIP": self._ip,
            "metadata": {"foo": "bar"}
        }

        m = Machine(data=test_obj)

        assert m.id == self._id
        assert m['id'] == self._id

        assert m.primaryIP == self._ip
        assert m['primaryIP'] == self._ip

        assert m.metadata == {"foo": "bar"}
        assert m['metadata'] == {"foo": "bar"}
