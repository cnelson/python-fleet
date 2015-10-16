import unittest

import os

from ..objects import Unit
from ..client import Client
from ..errors import APIError

from apiclient.http import HttpMockSequence


class TestUnit(unittest.TestCase):
    def setUp(self):
        self._BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    def _load_disccovery_fixture(self):
        fh = open(os.path.join(self._BASE_DIR, 'fixtures/fleet_v1.json'))
        discovery = fh.read()
        fh.close()

        return discovery

    def test_init_conflict(self):
        """If you specified data, you cannot specified, options, from_file, or from_string"""

        def test():
            Unit(data=True, options=True)

        def test2():
            Unit(data=True, from_file=True)

        def test3():
            Unit(data=True, from_string=True)

        self.assertRaises(ValueError, test)
        self.assertRaises(ValueError, test2)
        self.assertRaises(ValueError, test3)

    def test_init_multiple(self):
        """If data is not specified, you cannot specify more than one of options, from_file, from_string"""

        def test():
            Unit(options=True, from_string=True)

        def test2():
            Unit(options=True, from_file=True)

        def test3():
            Unit(options=True, from_string=True, from_file=True)

        self.assertRaises(ValueError, test)
        self.assertRaises(ValueError, test2)
        self.assertRaises(ValueError, test3)

    def test_blank(self):
        """A blank unit should come with a sane default state"""

        unit = Unit()

        assert unit.desiredState == 'launched'
        assert unit.options == []

    def test_from_file_good(self):
        """Passing in a file should cause it to be loaded"""

        # this should match the contents of the fixture below
        test_options = [{'section': 'Service', 'name': 'ExecStart', 'value': '/usr/bin/sleep 1d'}]

        unit = Unit(from_file=os.path.join(self._BASE_DIR, 'fixtures/test.service'))

        assert unit.options == test_options

    def test_from_file_bad(self):
        """IOError should be raised on non-existant files"""

        def test():
            Unit(from_file=os.path.join(self._BASE_DIR, 'fixtures/this-file-should-not-exist'))

        self.assertRaises(IOError, test)

    def test_from_string_good(self):
        """Loading from a good string works"""

        # these test values should be equal
        test_options = [{'section': 'Service', 'name': 'ExecStart', 'value': '/usr/bin/sleep 1d'}]
        test_string = "[Service]\n# comments should be ignored\nExecStart=/usr/bin/sleep 1d"

        unit = Unit(from_string=test_string)

        assert unit.options == test_options

    def test_from_string_bad(self):
        """ValueError should be raised for invalid unit string"""

        def test():
            Unit(from_string="SomeKey=WithNoSection")

        def test2():
            Unit(from_string="[Section]\nSome Line with No Equals")

        self.assertRaises(ValueError, test)
        self.assertRaises(ValueError, test2)

    def test_from_string_continuation_good(self):
        """When parsing unit files, line continuation with a trailing backslash works"""
        unit = Unit(from_string="[Section]\nThisLine=The start of \\\nsomething very\\\n long and boring\n")

        # test options (this should match the string above)
        test_options = [
            {
                'section': 'Section',
                'name': 'ThisLine',
                'value': 'The start of something very long and boring'
            }
        ]

        assert unit.options == test_options

    def test_options_no_desired_state(self):
        """Setting options explicitly works"""
        test_options = [{'section': 'Service', 'name': 'ExecStart', 'value': '/usr/bin/sleep 1d'}]

        unit = Unit(options=test_options)

        assert unit.options == test_options

    def test_options_desired_state(self):
        """Setting desiredState in constructor works"""
        test_options = [{'section': 'Service', 'name': 'ExecStart', 'value': '/usr/bin/sleep 1d'}]

        unit = Unit(desired_state='inactive', options=test_options)

        assert unit.options == test_options

        assert unit.desiredState == 'inactive'

    def test_repr(self):
        """repr shows entire object"""
        test_options = [{'section': 'Service', 'name': 'ExecStart', 'value': '/usr/bin/sleep 1d'}]

        unit = Unit(options=test_options)

        assert str(test_options) in repr(unit)

    def test_str_roundtrip(self):
        """Calling str() on a unit, should generate a systemd unit"""

        test_string = "[Service]\nExecStart=/usr/bin/sleep 1d"

        unit = Unit(from_string=test_string)

        assert test_string == str(unit)

    def test_is_live(self):
        """A unit is live if it as a client and data with a name key"""

        unit = Unit()

        assert unit._is_live() is False

        unit = Unit(client=True, data=None)

        assert unit._is_live() is False

        unit = Unit(client=True, data=None)

        assert unit._is_live() is False

        unit = Unit(client=True, data={'name': 'test'})

        assert unit._is_live()

    def test_add_option_dead(self):
        """We should be able to add options to non-live units"""
        test_options = [{'section': 'Service', 'name': 'ExecStart', 'value': '/usr/bin/sleep 1d'}]

        unit = Unit()

        unit.add_option('Service', 'ExecStart', '/usr/bin/sleep 1d')

        assert unit.options == test_options

    def test_add_option_live(self):
        """We should not be able to add options to non-live units"""

        def test():
            unit = Unit(client=True, data={'name': 'test'})
            unit.add_option('Service', 'ExecStart', '/usr/bin/sleep 1d')

        self.assertRaises(RuntimeError, test)

    def test_remove_option_live(self):
        """We should not be able to add options to non-live units"""

        def test():
            unit = Unit(client=True, data={'name': 'test'})
            unit.remove_option('Service', 'ExecStart', '/usr/bin/sleep 1d')

        self.assertRaises(RuntimeError, test)

    def test_remove_no_option(self):
        """Should return false when the item removed could not be found"""

        unit = Unit()

        assert unit.remove_option('Service', 'foo') is False
        assert unit.remove_option('Service', 'foo', 'bar') is False

    def test_remove_single_option(self):
        """We can remove a single option by value"""
        test_options = [
            {'section': 'Service', 'name': 'ExecStart', 'value': '/usr/bin/sleep 1d'},
            {'section': 'Service', 'name': 'ExecStartPre', 'value': '/bin/true'}
        ]

        unit = Unit()

        unit.add_option('Service', 'ExecStart', '/usr/bin/sleep 1d')
        unit.add_option('Service', 'ExecStartPre', '/bin/true')
        unit.add_option('Service', 'ExecStartPre', '/bin/false')

        assert unit.remove_option('Service', 'ExecStartPre', '/bin/false')

        assert test_options == unit.options

    def test_remove_all_option(self):
        """We can remove all options by name"""
        test_options = [
            {'section': 'Service', 'name': 'ExecStart', 'value': '/usr/bin/sleep 1d'}
        ]

        unit = Unit()

        unit.add_option('Service', 'ExecStart', '/usr/bin/sleep 1d')
        unit.add_option('Service', 'ExecStartPre', '/bin/true')
        unit.add_option('Service', 'ExecStartPre', '/bin/false')

        assert unit.remove_option('Service', 'ExecStartPre')

        assert test_options == unit.options

    def test_destroy_not_live(self):
        """Non live units cannot be destroyed"""

        def test():
            unit = Unit()
            unit.destroy()

        self.assertRaises(RuntimeError, test)

    def test_destroy_good(self):
        """We can destroy live units"""

        http = HttpMockSequence([
            ({'status': '200'}, self._load_disccovery_fixture()),
            ({'status': '204'}, None)
        ])

        client = Client('http://198.51.100.23:9160', http=http)

        unit = Unit(client=client, data={'name': 'test.service'})

        assert unit.destroy()

    def test_destroy_bad(self):
        """APIError is raised when non-existent units are destroyed"""

        def test():
            http = HttpMockSequence([
                ({'status': '200'}, self._load_disccovery_fixture()),
                ({'status': '404'}, '{"error":{"code":404,"message":"unit does not exist"}}')
            ])

            client = Client('http://198.51.100.23:9160', http=http)

            unit = Unit(client=client, data={'name': 'test.service'})
            unit.destroy()

        self.assertRaises(APIError, test)

    def test_desired_state_bad(self):
        """ValueError is raised when bad values are provided for desired state"""
        def test():
            unit = Unit()
            unit.set_desired_state('invalid-state')

        self.assertRaises(ValueError, test)

    def test_desired_state_good_dead(self):
        """We can set desired state on non-live objects"""
        unit = Unit()

        assert unit.desiredState == 'launched'

        assert unit.set_desired_state('inactive') == 'inactive'

        assert unit.desiredState == 'inactive'

    def test_desired_state_good_live(self):
        """We can set desired state on live objects"""

        http = HttpMockSequence([
            ({'status': '200'}, self._load_disccovery_fixture()),
            ({'status': '204'}, None),
            ({'status': '200'}, '{"currentState":"inactive","desiredState":"inactive","machineID":'
                                '"2901a44df0834bef935e24a0ddddcc23","name":"test.service","options"'
                                ':[{"name":"ExecStart","section":"Service","value":"/usr/bin/sleep 1d"}]}')
        ])

        client = Client('http://198.51.100.23:9160', http=http)

        unit = Unit(client=client, data={'name': 'test.service', 'desiredState': 'launched'})

        assert unit.desiredState == 'launched'

        assert unit.set_desired_state('inactive') == 'inactive'

        assert unit.desiredState == 'inactive'
