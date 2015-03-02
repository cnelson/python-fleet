import unittest

import uuid, json

from ..objects import FleetObject


class TestFleetObject(unittest.TestCase):
    """Basic tests for the FleetObject.

    This class isn't used directly, but is the parent class for Machine, Unit, and UnitState

    """

    def test_init(self):
        """Test constructor"""
        test_client = object()

        test_data = {
            uuid.uuid4().hex: uuid.uuid4().hex
        }

        fo = FleetObject(client=test_client, data=test_data)

        assert id(fo._client) == id(test_client)
        assert fo._data == test_data

    def test_update(self):
        """_update sets attributes"""
        fo = FleetObject()

        test_key = uuid.uuid4().hex
        test_val = uuid.uuid4().hex

        fo._update(test_key, test_val)

        assert getattr(fo, test_key) == test_val

    def test_contains_get_item_get_attr(self):
        """__contains__ works"""

        test_key = uuid.uuid4().hex
        test_val = uuid.uuid4().hex

        test_data = {
            test_key: test_val
        }

        fo = FleetObject(data=test_data)

        assert test_key in fo

        assert fo[test_key] == test_val

        assert getattr(fo, test_key) == test_val

    def test_setitem_setattr(self):
        """Setting items and attributes is not allowed"""
        test_key = uuid.uuid4().hex
        test_val = uuid.uuid4().hex

        fo = FleetObject()

        def test():
            fo[test_key] = test_val

        def test2():
            setattr(fo, test_key, test_val)

        self.assertRaises(AttributeError, test)
        self.assertRaises(AttributeError, test2)

    def test_str_repr(self):
        """str returns json"""

        test_key = uuid.uuid4().hex
        test_val = uuid.uuid4().hex

        test_data = {
            test_key: test_val
        }

        fo = FleetObject(data=test_data)

        assert test_data == json.loads(str(fo))

        assert test_key in repr(fo)
        assert test_val in repr(fo)

    def test_as_dict(self):
        """as_dict returns a dict"""
        test_key = uuid.uuid4().hex
        test_val = uuid.uuid4().hex

        test_data = {
            test_key: test_val
        }

        fo = FleetObject(data=test_data)

        assert test_data == fo.as_dict()
