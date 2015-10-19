try:  # pragma: no cover
    # python 2
    import httplib
except ImportError:  # pragma: no cover
    # python 3
    import http.client as httplib

import httplib2  # NOQA
import sys

try:  # pragma: no cover
    # python 2
    import urllib
    unquote = urllib.unquote
except AttributeError:  # pragma: no cover
    # python 3
    import urllib.parse
    unquote = urllib.parse.unquote


class SSHTunnelProxyInfo(httplib2.ProxyInfo):
    def __init__(self, sock):
        """A data structure for passing a socket to an httplib.HTTPConnection

        Args:
            sock (socket-like): A connected socket or socket-like object.

        """

        self.sock = sock


class HTTPOverSSHTunnel(httplib.HTTPConnection):
    """
    A hack for httplib2 that expects proxy_info to be a socket already connected
    to our target, rather than having to call connect() ourselves. This is used
    to provide basic SSH Tunnelling support.
    """

    def __init__(self, host, port=None, strict=None, timeout=None, proxy_info=None):
        """
            Setup an HTTP connection over an already connected socket.

            Args:
                host: ignored (exists for compatibility with parent)
                post: ignored (exists for compatibility with parent)
                strict: ignored (exists for compatibility with parent)
                timeout: ignored (exists for compatibility with parent)

                proxy_info (SSHTunnelProxyInfo): A SSHTunnelProxyInfo instance.

        """

        # do the needful
        httplib.HTTPConnection.__init__(self, host, port)

        # looks like the python2 and python3 versions of httplib differ
        # python2, executables any callables and returns the result as proxy_info
        # python3 passes the callable directly to this function :(
        if hasattr(proxy_info, '__call__'):
            proxy_info = proxy_info(None)

        # make sure we have a validate socket before we stash it
        if not proxy_info or not isinstance(proxy_info, SSHTunnelProxyInfo) or not proxy_info.sock:
            raise ValueError('This Connection must be suppplied an SSHTunnelProxyInfo via the proxy_info arg')

        # keep it
        self.sock = proxy_info.sock

    def connect(self):  # pragma: no cover
        """Do nothing"""
        # we don't need to connect, this functions job is to make sure
        # self.sock exists and is connected.  We did that in __init__
        # This is just here to keep other code in the parent from fucking
        # with our already connected socket :)
        pass

# Add our module to httplib2 via sorta monkey patching
# When a request is made, the class responsible for the scheme is looked up in this dict
# So we inject our schemes and capture the SSH tunnel requests
sys.modules['httplib2'].SCHEME_TO_CONNECTION['ssh+http'] = HTTPOverSSHTunnel
sys.modules['httplib2'].SCHEME_TO_CONNECTION['ssh+http+unix'] = HTTPOverSSHTunnel
