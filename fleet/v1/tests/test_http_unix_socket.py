import unittest
import socket

from ...http import UnixConnectionWithTimeout


class TestHttpUnixSocket(unittest.TestCase):

    def test_bad_socket_path(self):

        def test():
            unix = UnixConnectionWithTimeout('%2Fthis%2Fdoes%2Fnot%2Fexist.sock', timeout=1)
            unix.connect()

        self.assertRaises(socket.error, test)
