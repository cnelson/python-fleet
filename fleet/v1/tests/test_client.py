import unittest

import os

from apiclient.http import HttpMock, HttpMockSequence

from ..client import Client
from ..errors import APIError
from ..objects import Unit


class TestFleetClient(unittest.TestCase):
    def setUp(self):

        self._BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        self.discovery = HttpMock(
            os.path.join(self._BASE_DIR, 'fixtures/fleet_v1.json'),
            {'status': '200'}
        )

        self.endpoint = 'http://198.51.100.23:9160'
        self.client = Client(self.endpoint, http=self.discovery)

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
                None,
                {'status': '404'}
            )

            Client(self.endpoint, http=http)

        self.assertRaises(ValueError, test)

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
