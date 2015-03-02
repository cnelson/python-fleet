#!/usr/bin/env python2.7

# Sorta Monkey patch httplib2 to support unix socket
from fleet.http import UnixConnectionWithTimeout  # NOQA

from googleapiclient.discovery import build
import googleapiclient.errors

import json, socket  # NOQA

from fleet.v1.objects import *
from fleet.v1.errors import *


class Client(object):
    """A python wrapper for the fleet v1 API

    The fleet v1 API is documented here: https://github.com/coreos/fleet/blob/master/Documentation/api-v1.md

   """

    _API = 'fleet'
    _VERSION = 'v1'
    _STATES = ['inactive', 'loaded', 'launched']

    def __init__(self, endpoint, http=None):
        """Connect to the fleet API and generate a client based on it's Discovery Documentation

        Args:
            endpoint (str): Location of the fleet API. Supported schemes are:
                            http     : A http connection over a TCP socket.  A http connection over a TCP socket.
                                       ``http://127.0.0.1:49153``
                            http+unix: A http connect over a unix domain socket. You must escape the path / = %2F.
                                       ``http+unix://%2Fvar%2Frun%2Ffleet.sock``

            http (httplib2.Http): An instance of httplib2.Http or something that acts like it
                                  that HTTP requests will be made through.

                                  You shouldn't usually need to pass this, but if you do need to
                                  configure specific options for your http client, or want to
                                  pass in a mock for testing.  This is the place to do it.


        Raises:
            ValueError: The endpoint provided was not accessible.
        """

        # stash this for later
        self._endpoint = endpoint.strip('/')

        self._http = http

        # geneate a client binding using the google-api-python client.
        # See https://developers.google.com/api-client-library/python/start/get_started
        # For more infomation on how to use the generated client binding.

        try:
            discovery_url = self._endpoint + '/{api}/{apiVersion}/discovery'

            self._service = build(
                self._API,
                self._VERSION,
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
            response = json.loads(exc.content)['error']

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
