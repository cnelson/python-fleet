import unittest
import uuid, random

from ..errors import APIError


class TestAPIError(unittest.TestCase):

    def test_error(self):
        """Test constructor"""
        test_code = random.randint(400, 600)
        test_message = uuid.uuid4().hex
        test_http_error = object()

        ae = APIError(test_code, test_message, test_http_error)

        assert ae.code == test_code

        assert ae.message == test_message
        assert id(ae.http_error) == id(test_http_error)

        assert str(test_code) in str(ae)
        assert test_message in str(ae)

        assert str(test_code) in repr(ae)
        assert test_message in repr(ae)
