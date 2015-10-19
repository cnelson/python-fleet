#!/usr/bin/env python2.7

from googleapiclient.discovery import build
import googleapiclient.errors

import json, socket, os  # NOQA

import httplib2

import paramiko

from fleet.v1.objects import *
from fleet.v1.errors import *
from fleet.http.ssh_tunnel import SSHTunnelProxyInfo

try:  # pragma: no cover
    # python 2
    import urlparse
except ImportError:  # pragma: no cover
    # python 3
    import urllib.parse as urlparse

try:  # pragma: no cover
    # python 2
    import urllib
    unquote = urllib.unquote
except AttributeError:  # pragma: no cover
    # python 3
    import urllib.parse
    unquote = urllib.parse.unquote


class SSHTunnel(object):
    """Use paramiko to setup local "ssh -L" tunnels for Client to use"""

    def __init__(
        self,
        host,
        username=None,
        port=22,
        timeout=10,
        known_hosts_file=None,
        strict_host_key_checking=True
    ):
        """Connect to the SSH server, and authenticate

        Args:
            host (str or paramiko.transport.Transport): The hostname to connect to or an already connected Transport.
            username (str): The username to use when authenticating.
            port (int): The port to connect to, defaults to 22.
            timeout (int): The timeout to wait for a connection in seconds, defaults to 10.
            known_hosts_file (str): A path to a known host file, ignored if strict_host_key_checking is False.
            strict_host_key_checking (bool): Verify host keys presented by remote machines before
            initiating SSH connections, defaults to True.

        Raises:
            ValueError: strict_host_key_checking was true, but known_hosts_file didn't exist.
            socket.gaierror: Unable to resolve host
            socket.error: Unable to connect to host:port
            paramiko.ssh_exception.SSHException: Error authenticating during SSH connection.
        """

        self.client = None
        self.transport = None

        # if they passed us a transport, then we don't need to make our own
        if isinstance(host, paramiko.transport.Transport):
            self.transport = host
        else:
            # assume they passed us a hostname, and we connect to it
            self.client = paramiko.SSHClient()

            # if we are strict, then we have to have a host file
            if strict_host_key_checking:
                try:
                    self.client.load_system_host_keys(os.path.expanduser(known_hosts_file))
                except IOError:
                    raise ValueError(
                        'Strict Host Key Checking is enabled, but hosts file ({0}) '
                        'does not exist or is unreadable.'.format(known_hosts_file)
                    )
            else:
                # don't load the host file, and set to AutoAdd missing keys
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Connect to the host, with the provided params, let exceptions bubble up
            self.client.connect(
                host,
                port=port,
                username=username,
                banner_timeout=timeout,
            )

            # Stash our transport
            self.transport = self.client.get_transport()

    def forward_tcp(self, host, port):
        """Open a connection to host:port via an ssh tunnel.

        Args:
            host (str): The host to connect to.
            port (int): The port to connect to.

        Returns:
            A socket-like object that is connected to the provided host:port.

        """

        return self.transport.open_channel(
            'direct-tcpip',
            (host, port),
            self.transport.getpeername()
        )

    def forward_unix(self, path):
        """Open a connection to a unix socket via an ssh tunnel.

        Requires the server to be running OpenSSH >=6.7.

        Args:
            path (str): A path to a unix domain socket.

        Returns:
            A socket-like object that is connected to the provided path.

        Raises:
            RuntimeError: All the time because of what it says on the tin.

        """
        raise RuntimeError(
            'Paramiko does not yet support tunneling unix domain sockets. '
            'Help is needed to add this functionality! '
            'https://github.com/paramiko/paramiko/issues/544'
        )

        # when paramiko patches, hopefully this is all that is needed:
        # return self.transport.open_channel(
        #    'direct-streamlocal@openssh.com',
        #     path,
        #    self.transport.getpeername()
        # )


class Client(object):
    """A python wrapper for the fleet v1 API

    The fleet v1 API is documented here: https://github.com/coreos/fleet/blob/master/Documentation/api-v1.md

   """

    _API = 'fleet'
    _VERSION = 'v1'
    _STATES = ['inactive', 'loaded', 'launched']

    def __init__(
        self,
        endpoint,
        http=None,

        ssh_tunnel=None,
        ssh_username='core',
        ssh_timeout=10,
        ssh_known_hosts_file='~/.fleetctl/known_hosts',
        ssh_strict_host_key_checking=True,

        ssh_raw_transport=None
    ):

        """Connect to the fleet API and generate a client based on it's discovery document.

        Args:
            endpoint (str): A URL where the fleet API can be reached.  Supported schemes are:
                http: A HTTP connection over a TCP socket.
                    Example: http://127.0.0.1:49153
                http+unix: A HTTP connection over a unix domain socket. You must escape the path (/ = %2F).
                    Example: http+unix://%2Fvar%2Frun%2Ffleet.sock

            http (httplib2.Http): An instance of httplib2.Http (or something that acts like it) that HTTP requests will
            be made through. You do not need to pass this unless you need to configure specific options for your
            http client, or want to pass in a mock for testing.

            ssh_tunnel (str '<host>[:<port>]'): Establish an SSH tunnel through the provided address for communication
            with fleet. Defaults to None. If specified, the following other options adjust it's behaivor:
                ssh_username (str): Username to use when connecting to SSH, defaults to 'core'.
                ssh_timeout (float): Amount of time in seconds to allow for SSH connection initialization
                before failing, defaults to 10.
                ssh_known_hosts_file (str): File used to store remote machine fingerprints,
                defaults to '~/.fleetctl/known_hosts'.  Ignored if `ssh_strict_host_key_checking` is False
                ssh_strict_host_key_checking (bool): Verify host keys presented by remote machines before
                initiating SSH connections, defaults to True.

            ssh_raw_transport (paramiko.transport.Transport): An active Transport on which open_channel() will be
            called to establish connections.

            See Advanced SSH Tunneling in docs/client.md for more information.

        Raises:
            ValueError: The endpoint provided was not accessible or your ssh configuration is incorrect
        """

        # stash this for later
        self._endpoint = endpoint.strip('/')
        self._ssh_client = None

        # we overload the http when our proxy enabled versin if they request ssh tunneling
        # so we need to make sure they didn't give us both
        if (ssh_tunnel or ssh_raw_transport) and http:
            raise ValueError('You cannot specify your own http client, and request ssh tunneling.')

        # only one way to connect, not both
        if ssh_tunnel and ssh_raw_transport:
            raise ValueError('If ssh_tunnel is specified, ssh_raw_transport must be None')

        # see if we need to setup an ssh tunnel
        self._ssh_tunnel = None

        # if they handed us a transport, then we either bail or are good to go
        if ssh_raw_transport:
            if not isinstance(ssh_raw_transport, paramiko.transport.Transport):
                raise ValueError('ssh_raw_transport must be an active instance of paramiko.transport.Transport.')

            self._ssh_tunnel = SSHTunnel(host=ssh_raw_transport)

        # otherwise we are connecting ourselves
        elif ssh_tunnel:
            (ssh_host, ssh_port) = self._split_hostport(ssh_tunnel, default_port=22)

            try:
                self._ssh_tunnel = SSHTunnel(
                    host=ssh_host,
                    port=ssh_port,
                    username=ssh_username,
                    timeout=ssh_timeout,
                    known_hosts_file=ssh_known_hosts_file,
                    strict_host_key_checking=ssh_strict_host_key_checking
                )

            except socket.gaierror as exc:
                raise ValueError('{0} could not be resolved.'.format(ssh_host))

            except socket.error as exc:
                raise ValueError('Unable to connect to {0}:{1}: {2}'.format(
                    ssh_host,
                    ssh_port,
                    exc
                ))

            except paramiko.ssh_exception.SSHException as exc:
                raise ValueError('Unable to connect via ssh: {0}: {1}'.format(
                    exc.__class__.__name__,
                    exc
                ))

        # did we get an ssh connection up?
        if self._ssh_tunnel:
            # inject the SSH tunnel socketed into httplib via the proxy_info interface
            self._http = httplib2.Http(proxy_info=self._get_proxy_info)

            # preface our scheme with 'ssh+'; httplib2's SCHEME_TO_CONNECTION
            # will invoke our custom connection objects and route the HTTP
            # call across the SSH connection established or passed in above
            self._endpoint = 'ssh+' + self._endpoint
        else:
            self._http = http

        # if we've made it this far, we are ready to try to talk to fleet
        # possibly through a proxy...

        # generate a client binding using the google-api-python client.
        # See https://developers.google.com/api-client-library/python/start/get_started
        # For more infomation on how to use the generated client binding.
        try:
            discovery_url = self._endpoint + '/{api}/{apiVersion}/discovery'

            self._service = build(
                self._API,
                self._VERSION,
                cache_discovery=False,
                discoveryServiceUrl=discovery_url,
                http=self._http
            )
        except socket.error as exc:  # pragma: no cover
            raise ValueError('Unable to connect to endpoint {0}: {1}'.format(
                self._endpoint,
                exc
            ))
        except googleapiclient.errors.UnknownApiNameOrVersion as exc:
            raise ValueError(
                'Connected to endpoint {0} but it is not a fleet v1 API endpoint. '
                'This usually means a GET request to {0}/{1}/{2}/discovery failed.'.format(
                    self._endpoint,
                    self._API,
                    self._VERSION
                ))

    def _split_hostport(self, hostport, default_port=None):
        """Split a string in the format of '<host>:<port>' into it's component parts

        default_port will be used if a port is not included in the string

        Args:
            str ('<host>' or '<host>:<port>'): A string to split into it's parts

        Returns:
            two item tuple: (host, port)

        Raises:
            ValueError: The string was in an invalid element
        """

        try:
            (host, port) = hostport.split(':', 1)
        except ValueError:  # no colon in the string so make our own port
            host = hostport

            if default_port is None:
                raise ValueError('No port found in hostport, and default_port not provided.')

            port = default_port

        try:
            port = int(port)
            if port < 1 or port > 65535:
                raise ValueError()
        except ValueError:
            raise ValueError("{0} is not a valid TCP port".format(port))

        return (host, port)

    def _endpoint_to_target(self, endpoint):
        """Convert a URL into a host / port, or into a path to a unix domain socket

        Args:
            endpoint (str): A URL parsable by urlparse

        Returns:
            3 item tuple: (host, port, path).
            host and port will None, and path will be not None if a a unix domain socket URL is passed
            path will be None if a normal TCP based URL is passed

        """
        parsed = urlparse.urlparse(endpoint)
        scheme = parsed[0]
        hostport = parsed[1]

        if 'unix' in scheme:
            return (None, None, unquote(hostport))

        if scheme == 'https':
            target_port = 443
        else:
            target_port = 80

        (target_host, target_port) = self._split_hostport(hostport, default_port=target_port)
        return (target_host, target_port, None)

    def _get_proxy_info(self, _=None):
        """Generate a ProxyInfo class from a connected SSH transport

        Args:
            _ (None): Ignored.  This is just here as the ProxyInfo spec requires it.


        Returns:
            SSHTunnelProxyInfo: A ProxyInfo with an active socket tunneled through SSH

        """
        # parse the fleet endpoint url, to establish a tunnel to that host
        (target_host, target_port, target_path) = self._endpoint_to_target(self._endpoint)

        # implement the proxy_info interface from httplib which requires
        # that we accept a scheme, and return a ProxyInfo object
        # we do :P
        # This is called once per request, so we keep this here
        # so that we can keep one ssh connection open, and allocate
        # new channels as needed per-request
        sock = None

        if target_path:
            sock = self._ssh_tunnel.forward_unix(path=target_path)
        else:
            sock = self._ssh_tunnel.forward_tcp(target_host, port=target_port)

        # Return a ProxyInfo class with this socket
        return SSHTunnelProxyInfo(sock=sock)

    def _single_request(self, method, *args, **kwargs):
        """Make a single request to the fleet API endpoint

        Args:
            method (str): A dot delimited string indicating the method to call.  Example: 'Machines.List'
            *args: Passed directly to the method being called.
            **kwargs: Passed directly to the method being called.

        Returns:
            dict: The response from the method called.

        Raises:
            fleet.v1.errors.APIError: Fleet returned a response code >= 400
        """

        # The auto generated client binding require instantiating each object you want to call a method on
        # For example to make a request to /machines for the list of machines you would do:
        # self._service.Machines().List(**kwargs)
        # This code iterates through the tokens in `method` and instantiates each object
        # Passing the `*args` and `**kwargs` to the final method listed

        # Start here
        _method = self._service

        # iterate over each token in the requested method
        for item in method.split('.'):

            # if it's the end of the line, pass our argument
            if method.endswith(item):
                _method = getattr(_method, item)(*args, **kwargs)
            else:
                # otherwise, just create an instance and move on
                _method = getattr(_method, item)()

        # Discovered endpoints look like r'$ENDPOINT/path/to/method' which isn't a valid URI
        # Per the fleet API documentation:
            # "Note that this discovery document intentionally ships with an unusable rootUrl;
            # clients must initialize this as appropriate."

        # So we follow the documentation, and replace the token with our actual endpoint
        _method.uri = _method.uri.replace('$ENDPOINT', self._endpoint)

        # Execute the method and return it's output directly
        try:
            return _method.execute(http=self._http)
        except googleapiclient.errors.HttpError as exc:
            response = json.loads(exc.content.decode('utf-8'))['error']

            raise APIError(code=response['code'], message=response['message'], http_error=exc)

    def _request(self, method, *args, **kwargs):
        """Make a request with automatic pagination handling

        Args:
            method (str): A dot delimited string indicating the method to call.  Example: 'Machines.List'
            *args: Passed directly to the method being called.
            **kwargs: Passed directly to the method being called.
                        Note: This method will inject the 'nextPageToken' key into `**kwargs` as needed to handle
                        pagination overwriting any value specified by the caller.  If you wish to handle pagination
                        manually use the `_single_request` method


        Yields:
            dict: The next page of responses from the method called.


        Raises:
            fleet.v1.errors.APIError: Fleet returned a response code >= 400

        """

        # This is set to False and not None so that the while loop below will execute at least once
        next_page_token = False

        while next_page_token is not None:
            # If bool(next_page_token), then include it in the request
            # We do this so we don't pass it in the initial request as we set it to False above
            if next_page_token:
                kwargs['nextPageToken'] = next_page_token

            # Make the request
            response = self._single_request(method, *args, **kwargs)

            # If there is a token for another page in the response, capture it for the next loop iteration
            # If not, we set it to None so that the loop will terminate
            next_page_token = response.get('nextPageToken', None)

            # Return the current response
            yield response

    def create_unit(self, name, unit):
        """Create a new Unit in the cluster

        Create and modify Unit entities to communicate to fleet the desired state of the cluster.
        This simply declares what should be happening; the backend system still has to react to
        the changes in this desired state. The actual state of the system is communicated with
        UnitState entities.


        Args:
            name (str): The name of the unit to create
            unit (Unit): The unit to submit to fleet

        Returns:
            Unit: The unit that was created

        Raises:
            fleet.v1.errors.APIError: Fleet returned a response code >= 400

        """

        self._single_request('Units.Set', unitName=name, body={
            'desiredState': unit.desiredState,
            'options': unit.options
        })

        return self.get_unit(name)

    def set_unit_desired_state(self, unit, desired_state):
        """Update the desired state of a unit running in the cluster

        Args:
            unit (str, Unit): The Unit, or name of the unit to update

            desired_state: State the user wishes the Unit to be in
                          ("inactive", "loaded", or "launched")
        Returns:
            Unit: The unit that was updated

        Raises:
            fleet.v1.errors.APIError: Fleet returned a response code >= 400
            ValueError: An invalid value was provided for ``desired_state``

        """

        if desired_state not in self._STATES:
            raise ValueError('state must be one of: {0}'.format(
                self._STATES
            ))

        # if we are given an object, grab it's name property
        # otherwise, convert to unicode
        if isinstance(unit, Unit):
            unit = unit.name
        else:
            unit = str(unit)

        self._single_request('Units.Set', unitName=unit, body={
            'desiredState': desired_state
        })

        return self.get_unit(unit)

    def destroy_unit(self, unit):
        """Delete a unit from the cluster

        Args:
            unit (str, Unit): The Unit, or name of the unit to delete

        Returns:
            True: The unit was deleted

        Raises:
            fleet.v1.errors.APIError: Fleet returned a response code >= 400

        """

        # if we are given an object, grab it's name property
        # otherwise, convert to unicode
        if isinstance(unit, Unit):
            unit = unit.name
        else:
            unit = str(unit)

        self._single_request('Units.Delete', unitName=unit)
        return True

    def list_units(self):
        """Return the current list of the Units in the fleet cluster

        Yields:
            Unit: The next Unit in the cluster

        Raises:
            fleet.v1.errors.APIError: Fleet returned a response code >= 400

        """
        for page in self._request('Units.List'):
            for unit in page.get('units', []):
                yield Unit(client=self, data=unit)

    def get_unit(self, name):
        """Retreive a specifi unit from the fleet cluster by name

        Args:
            name (str): If specified, only this unit name is returned

        Returns:
            Unit: The unit identified by ``name`` in the fleet cluster

        Raises:
            fleet.v1.errors.APIError: Fleet returned a response code >= 400

        """
        return Unit(client=self, data=self._single_request('Units.Get', unitName=name))

    def list_unit_states(self, machine_id=None, unit_name=None):
        """Return the current UnitState for the fleet cluster

        Args:
            machine_id (str): filter all UnitState objects to those
                              originating from a specific machine

            unit_name (str):  filter all UnitState objects to those related
                              to a specific unit

        Yields:
            UnitState: The next UnitState in the cluster

        Raises:
            fleet.v1.errors.APIError: Fleet returned a response code >= 400

        """
        for page in self._request('UnitState.List', machineID=machine_id, unitName=unit_name):
            for state in page.get('states', []):
                yield UnitState(data=state)

    def list_machines(self):
        """Retrieve a list of machines in the fleet cluster

        Yields:
            Machine: The next machine in the cluster

        Raises:
            fleet.v1.errors.APIError: Fleet returned a response code >= 400

        """
        # loop through each page of results
        for page in self._request('Machines.List'):
            # return each machine in the current page
            for machine in page.get('machines', []):
                yield Machine(data=machine)
