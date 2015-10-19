import unittest
import mock

import os, socket, tempfile  # NOQA

from apiclient.http import HttpMock, HttpMockSequence

import paramiko

from ..client import Client, SSHTunnel
from ..errors import APIError
from ..objects import Unit


class ForwardChecker(object):
    """A simple mock for SSHTunnel with this class when we don't actually want to connect to servers during tests"""
    def __init__(self, *args, **kwargs):
        pass

    def forward_tcp(self, host, port):
        return [host, port]

    def forward_unix(self, path):
        return path


class TestSSHTunnel(unittest.TestCase):
    def test_good_raw_transport(self):
        """Passing a raw transport to ssh tunnel skips other configuration"""
        t = paramiko.transport.Transport(None)

        s = SSHTunnel(host=t)

        assert s.client is None
        assert id(s.transport) == id(t)

    def test_bad_known_host_file(self):
        """If known_hosts_file doesn't exist but strict_host_key_checking is True, then a ValueError is raised"""
        tmpdir = tempfile.mkdtemp()

        bad_host_file = os.path.join(tmpdir, 'known_hosts')

        def test():
            SSHTunnel(host='foo', known_hosts_file=bad_host_file, strict_host_key_checking=True)

        os.rmdir(tmpdir)

        self.assertRaises(ValueError, test)

    def test_unix_forward(self):
        """Forwarding a unix domain socket raises RuntimeError"""
        t = paramiko.transport.Transport(None)

        s = SSHTunnel(host=t)

        def test():
            s.forward_unix('/tmp/socket')

        self.assertRaises(RuntimeError, test)

    def test_good_connect(self):
        """When we connect with a good client, the transport gets set correctly"""

        with mock.patch('paramiko.SSHClient'):
            s = SSHTunnel(host='foo', strict_host_key_checking=False)
            assert id(s.client.get_transport()) == id(s.transport)


class TestFleetClient(unittest.TestCase):
    def setUp(self):

        self._BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        self.discovery = self._get_discovery()

        self.endpoint = 'http://198.51.100.23:9160'
        self.client = Client(self.endpoint, http=self.discovery)

    def _get_discovery(self, *args, **kwargs):
        return HttpMock(
            os.path.join(self._BASE_DIR, 'fixtures/fleet_v1.json'),
            {'status': '200'}
        )

    def mock(self, http):
        self.client._http = http

    def test_init(self):
        """Test constructor"""
        assert self.client._endpoint == 'http://198.51.100.23:9160'
        assert id(self.client._http) == id(self.discovery)

    def test_init_endpoint_active_but_invalid(self):
        """Accessible endpoint with no discovery document"""

        def test():

            http = HttpMock(
                os.path.join(self._BASE_DIR, 'fixtures/empty_response.txt'),
                {'status': '404'},
            )

            Client(self.endpoint, http=http)

        self.assertRaises(ValueError, test)

    def test_init_ssh_tunnel_conflicting_params(self):
        """Providing conflicting parameters raises ValueError"""

        def test_tunnel_with_http():
            Client(self.endpoint, http=True, ssh_tunnel=True)

        def test_raw_with_http():
            Client(self.endpoint, http=True, ssh_raw_transport=True)

        def test_both_with_http():
            Client(self.endpoint, http=True, ssh_tunnel=True, ssh_raw_transport=True)

        def test_both():
            Client(self.endpoint, http=True, ssh_tunnel=True, ssh_raw_transport=True)

        for test in [test_tunnel_with_http, test_raw_with_http, test_both_with_http, test_both]:
            self.assertRaises(ValueError, test)

    def test_bad_transport_value(self):
        """Providing anything but a paramiko.transport.Transport to ssh_raw_transport raises ValueError"""

        def test():
            Client(endpoint=self.endpoint, ssh_raw_transport=True)

        self.assertRaises(ValueError, test)

    def test_hostport_split_default_port(self):
        """Validate that when passing a default port it's used when no port is provided"""
        result = self.client._split_hostport('foo', default_port=916)

        assert result == ('foo', 916)

        result = self.client._split_hostport('foo:22', default_port=916)

        assert result == ('foo', 22)

    def test_hostport_split_no_port(self):
        """ValueError is raised if no port is passted to hostport_split"""

        def test():
            self.client._split_hostport('foo')

        self.assertRaises(ValueError, test)

    def test_hostport_split_not_int(self):
        """ValueError is raised if a non number port is passed"""

        def test():
            self.client._split_hostport('foo:bar')

        self.assertRaises(ValueError, test)

    def test_hostport_split_not_in_range(self):
        """ValueError is raised if port is out of range"""

        def test():
            self.client._split_hostport('foo:99999')

        self.assertRaises(ValueError, test)

    def test_endpoint_to_target_unix(self):
        """When passing in a http+unix endpoint, we receive the path pack with no host/port"""
        result = self.client._endpoint_to_target('http+unix://%2Ftmp%2Fsocket')

        assert result == (None, None, '/tmp/socket')

    def test_endpoint_to_target_https_default_port(self):
        """When passing in a https endpoint with no port, port 443 is returned"""
        result = self.client._endpoint_to_target('https://foo')

        assert result == ('foo', 443, None)

    def test_endpoint_to_target_http_default_port(self):
        """When passing in a https endpoint with no port, port 443 is returned"""
        result = self.client._endpoint_to_target('http://foo')

        assert result == ('foo', 80, None)

    def test_endpoint_to_target_explicit_port(self):
        """An explicit port is used if provided regardless of scheme"""
        result = self.client._endpoint_to_target('http://foo:999')

        assert result == ('foo', 999, None)

        result = self.client._endpoint_to_target('https://foo:888')

        assert result == ('foo', 888, None)

    def test_get_proxy_info_tcp(self):
        """When given a TCP based endpoint, an open channel is returned"""

        self.client._ssh_tunnel = ForwardChecker()
        result = self.client._get_proxy_info()

        assert result.sock == ['198.51.100.23', 9160]

    def test_get_proxy_info_unix(self):
        """When given a TCP based endpoint, an open channel is returned"""

        self.client._endpoint = 'http+unix://%2Ftmp%2Fsocket'
        self.client._ssh_tunnel = ForwardChecker()
        result = self.client._get_proxy_info()

        assert result.sock == '/tmp/socket'

    def test_ssh_tunnel_bad_host(self):
        """When SSHClient returns a socket.gaierror for a bad hostname, we return ValueError"""
        def test():
            with mock.patch('paramiko.SSHClient', side_effect=socket.gaierror):
                Client(endpoint=self.endpoint, ssh_tunnel='unknown_host')

        self.assertRaises(ValueError, test)

    def test_ssh_tunnel_bad_port(self):
        """When SSHClient returns a socket.error for a bad port, we return ValueError"""
        def test():
            with mock.patch('paramiko.SSHClient', side_effect=socket.error):
                Client(endpoint=self.endpoint, ssh_tunnel='unknown_host:2222')

        self.assertRaises(ValueError, test)

    def test_ssh_tunnel_ssh_error(self):
        """When SSHClient returns an error authenticating, we return ValueError"""
        def test():
            with mock.patch('paramiko.SSHClient', side_effect=paramiko.ssh_exception.SSHException):
                Client(endpoint=self.endpoint, ssh_tunnel='host-ok-bad-key')

        self.assertRaises(ValueError, test)

    def test_ssh_tunnel_with_unix(self):
        """RuntimeError is raised if we try to forward a unix domain socket"""

        t = paramiko.transport.Transport(None)

        s = SSHTunnel(host=t)

        def test():
            s.forward_unix('/tmp/socket')

        self.assertRaises(RuntimeError, test)

    def test_single_request_good(self):
        """A single request returns 200"""
        self.mock(HttpMock(
            os.path.join(self._BASE_DIR, 'fixtures/machines_single_no_metadata.json'),
            {'status': '200'}
        ))

        output = self.client._single_request('Machines.List')

        assert 'machines' in output

    def test_single_request_bad(self):
        """A 404 return causes APIError to be raised"""

        def test():
            self.mock(HttpMockSequence([
                ({'status': '404'}, '{"error":{"code":404,"message":"unit does not exist"}}')
            ]))

            self.client._single_request('Units.Get', unitName='test.service')

        self.assertRaises(APIError, test)

    def test_request_with_no_pagination(self):
        """A paging request with no second page works"""
        self.mock(HttpMock(
            os.path.join(self._BASE_DIR, 'fixtures/machines_single_no_metadata.json'),
            {'status': '200'}
        ))

        output = list(self.client._request('Machines.List'))

        assert len(output) == 1

        assert 'machines' in output[0]

    def test_request_with_pagination(self):
        """Pagination works automatcally"""

        self.mock(HttpMockSequence([
            ({'status': '200'}, '{"machines":[{"id":"b4104f4b83fd48b2acc16a085b0ec2ce","primaryIP":"198.51.100.99"}],'
                                '"nextPageToken": "foo"}'),
            ({'status': '200'}, '{"machines":[{"id":"b4104f4b83fd48b2acc16a085b0ec2ce","primaryIP":"198.51.100.99"}]}')
        ]))

        output = list(self.client._request('Machines.List'))

        assert len(output) == 2

        assert 'machines' in output[0]
        assert 'machines' in output[1]

    def test_create_unit(self):
        """Create a unit"""
        self.mock(HttpMockSequence([
            ({'status': '201'}, None),
            ({'status': '200'}, '{"currentState":"launched","desiredState":"launched","machineID":'
                                '"b4104f4b83fd48b2acc16a085b0ec2ce","name":"test.service","options":'
                                '[{"name":"ExecStart","section":"Service","value":"/usr/bin/sleep 1d"}]}')
        ]))

        unit = self.client.create_unit(
            'test.service',
            Unit(from_file=os.path.join(self._BASE_DIR, 'fixtures/test.service'))
        )

        assert unit
        assert unit.name == 'test.service'

    def test_set_unit_desired_state_bad(self):
        """ValueError is raised when an invalid state is passed"""

        def test():
            self.client.set_unit_desired_state('test.service', 'invalid-state')

        self.assertRaises(ValueError, test)

    def test_set_unit_name_desired_state_good(self):
        """Unit Desired State can be updated by name"""

        self.mock(HttpMockSequence([
            ({'status': '204'}, None),
            ({'status': '200'}, '{"currentState":"launched","desiredState":"inactive","machineID":'
                                '"b4104f4b83fd48b2acc16a085b0ec2ce","name":"test.service","options":'
                                '[{"name":"ExecStart","section":"Service","value":"/usr/bin/sleep 1d"}]}')
        ]))

        unit = self.client.set_unit_desired_state('test.service', 'inactive')

        assert unit
        assert unit.desiredState == 'inactive'

    def test_set_unit_obj_desired_state_good(self):
        """Unit Desired State can be updated by object"""

        self.mock(HttpMockSequence([
            ({'status': '204'}, None),
            ({'status': '200'}, '{"currentState":"launched","desiredState":"inactive","machineID":'
                                '"b4104f4b83fd48b2acc16a085b0ec2ce","name":"test.service","options":'
                                '[{"name":"ExecStart","section":"Service","value":"/usr/bin/sleep 1d"}]}')
        ]))

        unit = Unit(from_file=os.path.join(self._BASE_DIR, 'fixtures/test.service'))
        unit._update('name', 'test.service')

        unit = self.client.set_unit_desired_state(unit, 'inactive')

        assert unit
        assert unit.desiredState == 'inactive'

    def test_destroy_unit_name(self):
        """Destroy a unit by name"""
        self.mock(HttpMockSequence([
            ({'status': '204'}, None),
        ]))

        assert self.client.destroy_unit('test.service')

    def test_destroy_unit_obj(self):
        """Destroy a unit by object"""

        self.mock(HttpMockSequence([
            ({'status': '204'}, None),
        ]))

        unit = Unit(from_file=os.path.join(self._BASE_DIR, 'fixtures/test.service'))
        unit._update('name', 'test.service')

        assert self.client.destroy_unit(unit)

    def test_list_units(self):
        """List units"""
        self.mock(HttpMockSequence([
            ({'status': '200'}, '{"units":[{"currentState":"launched","desiredState":"launched","machineID":'
                                '"b4104f4b83fd48b2acc16a085b0ec2ce","name":"foo.service","options":'
                                '[{"name":"ExecStart","section":"Service","value":"/usr/bin/sleep 1d"}]}], '
                                '"nextPageToken": "foo"}'),
            ({'status': '200'}, '{"units":[{"currentState":"launched","desiredState":"launched","machineID":'
                                '"b4104f4b83fd48b2acc16a085b0ec2ce","name":"foo.service","options":'
                                '[{"name":"ExecStart","section":"Service","value":"/usr/bin/sleep 1d"}]}]}')
        ]))

        units = list(self.client.list_units())

        assert len(units) == 2

        assert 'name' in units[0]
        assert 'name' in units[1]

    def test_get_unit(self):
        """Get an individual unit"""
        self.mock(HttpMockSequence([
            ({'status': '200'}, '{"currentState":"launched","desiredState":"launched","machineID":'
                                '"b4104f4b83fd48b2acc16a085b0ec2ce","name":"test.service","options":'
                                '[{"name":"ExecStart","section":"Service","value":"/usr/bin/sleep 1d"}]}')
        ]))

        unit = self.client.get_unit('test.service')

        assert 'name' in unit

    def test_list_unit_states(self):
        """List unit states"""
        self.mock(HttpMockSequence([
            ({'status': '200'}, '{"states":[{"hash":"dd401fa78c2de99a9c4045cbb4b285679067acf6","machineID":'
                                '"b4104f4b83fd48b2acc16a085b0ec2ce","name":"foo.service","systemdActiveState":'
                                '"active","systemdLoadState":"loaded","systemdSubState":"running"}], "nextPageToken":'
                                '"foo"}'),
            ({'status': '200'}, '{"states":[{"hash":"dd401fa78c2de99a9c4045cbb4b285679067acf6","machineID":'
                                '"b4104f4b83fd48b2acc16a085b0ec2ce","name":"foo.service","systemdActiveState":'
                                '"active","systemdLoadState":"loaded","systemdSubState":"running"}]}')
        ]))

        unitstates = list(self.client.list_unit_states())

        assert len(unitstates) == 2

        assert 'hash' in unitstates[0]
        assert 'hash' in unitstates[1]

    def test_list_machines(self):
        """List Machines"""
        self.mock(HttpMock(
            os.path.join(self._BASE_DIR, 'fixtures/machines_single_no_metadata.json'),
            {'status': '200'}
        ))

        machines = list(self.client.list_machines())

        assert len(machines) == 1

        assert 'id' in machines[0]
