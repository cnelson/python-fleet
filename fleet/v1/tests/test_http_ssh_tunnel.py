import unittest

from ...http import HTTPOverSSHTunnel, SSHTunnelProxyInfo


class TestHttpSSHTunnel(unittest.TestCase):

    def test_proxy_info_callable(self):
        """Passing a callable to proxy_info gets executed"""

        def test(_):
            return SSHTunnelProxyInfo('lolz')

        h = HTTPOverSSHTunnel('foo', proxy_info=test)

        assert h.sock == 'lolz'

    def test_proxy_info_data(self):
        """Passing data to proxy_info gets returned"""

        h = HTTPOverSSHTunnel('foo', proxy_info=SSHTunnelProxyInfo('lolz'))

        assert h.sock == 'lolz'

    def test_proxy_info_bad_object(self):
        """Passing anything other than proxy info causes an error"""

        def test():
            HTTPOverSSHTunnel('foo', proxy_info='lolz')

        self.assertRaises(ValueError, test)
