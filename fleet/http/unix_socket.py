try:  # pragma: no cover
    # python 2
    import httplib
except ImportError:  # pragma: no cover
    # python 3
    import http.client as httplib

import httplib2  # NOQA
import socket
import sys

try:  # pragma: no cover
    # python 2
    import urllib
    unquote = urllib.unquote
except AttributeError:  # pragma: no cover
    # python 3
    import urllib.parse
    unquote = urllib.parse.unquote


def has_timeout(timeout):  # pragma: no cover
    if hasattr(socket, '_GLOBAL_DEFAULT_TIMEOUT'):
        return (timeout is not None and timeout is not socket._GLOBAL_DEFAULT_TIMEOUT)
    return (timeout is not None)


class UnixConnectionWithTimeout(httplib.HTTPConnection):
    """
    HTTPConnection subclass that supports timeouts

    All timeouts are in seconds. If None is passed for timeout then
    Python's default timeout for sockets will be used. See for example
    the docs of socket.setdefaulttimeout():
    http://docs.python.org/library/socket.html#socket.setdefaulttimeout
    """

    def __init__(self, host, port=None, strict=None, timeout=None, proxy_info=None):
        httplib.HTTPConnection.__init__(self, host, port)
        self.timeout = timeout

    def connect(self):
        """Setup the unix domain socket.

        We don't actually connect until ``request`` because httplib2 doesn't given us the path in this method :(

        """
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

            if has_timeout(self.timeout):
                self.sock.settimeout(self.timeout)

            self.sock.connect(unquote(self.host))
        except socket.error as msg:
            if self.sock:
                self.sock.close()
            self.sock = None

            raise socket.error(msg)

# Add our module to httplib2 via sorta monkey patching
sys.modules['httplib2'].SCHEME_TO_CONNECTION['http+unix'] = UnixConnectionWithTimeout
