# Client

A python wrapper for the fleet v1 API

[Offical Fleet v1 API Documentation](https://github.com/coreos/fleet/blob/master/Documentation/api-v1.md)

## Creating Clients

Connect to the fleet API and generate a client based on it's Discovery Documentation

### Client(self, endpoint, http=None)
* **endpoint (str):**  Location of the fleet API.  Supported schemes are:
    * **http     :** A http connection over a TCP socket.  ``http://127.0.0.1:49153``
    * **http+unix:** A http connect over a unix domain socket. You must escape the path / = %2F. ``http+unix://%2Fvar%2Frun%2Ffleet.sock``


* **http (httplib2.Http):** An instance of httplib2.Http or something that acts like it that HTTP requests will be made through.
You shouldn't usually need to pass this, but if you do need to configure specific options for your http client, or want to pass in a mock for testing.  This is the place to do it.

### Raises
* **ValueError:** The endpoint provided was not accessable.

### Example

    >>> import fleet.v1 as fleet

    # connect over tcp
    >>> fleet_client = fleet.Client('http://127.0.0.1:49153')

    # or over a unix domain socket
    >>> fleet_client = fleet.Client('http+unix://%2Fvar%2Frun%2Ffleet.sock')


## create_unit()

Create a new [Unit](unit.md) in the cluster

### create_unit(self, name, unit)
* **name (str):** The name of the unit to create
* **unit ([Unit](unit.md)):** The unit to submit to fleet 

### Returns
* [Unit](unit.md): The unit that was created

### Raises
* [APIError](apierror.md): Fleet returned a response code >= 400

### Example

    >>> fleet_client.create_unit('foo.service', fleet.Unit(from_file='foo.service'))
    <Unit: {u'desiredState': u'launched', u'name': u'foo.service', u'currentState': u'inactive', u'options': [{u'section': u'Service', u'name': u'ExecStart', u'value': u'/usr/bin/sleep 1d'}]}>


## set_unit_desired_state()

Update the desired state of a unit running in the cluster.

### set_unit_desired_state(self, unit, desired_state)
* **unit (str, [Unit](unit)):** The Unit, or name of the unit to delete
* **desired_state (str)**: State the user wishes the Unit to be in  ("inactive", "loaded", or "launched")

### Returns
* [Unit](unit.md): The updated unit

### Raises
* [APIError](apierror.md): Fleet returned a response code >= 400
* **ValueError:** An invalid value was provided for ``desired_state``


### Example
    >>> unit = fleet_client.create_unit('foo.service', fleet.Unit(from_file='foo.service'))
    >>> unit.name
    u'foo.service'
    >>> unit.desiredState
    u'launched'

    # reference the object directly
    >>> fleet_client.set_unit_desired_state(unit, 'inactive')
    <Unit: {u'desiredState': u'inactive', u'name': u'foo.service', u'currentState': u'inactive', u'options': [{u'section': u'Service', u'name': u'ExecStart', u'value': u'/usr/bin/sleep 1d'}]}>

    # or it's name
    >>> fleet_client.set_unit_desired_state('foo.service', 'inactive')
    <Unit: {u'desiredState': u'inactive', u'name': u'foo.service', u'currentState': u'inactive', u'options': [{u'section': u'Service', u'name': u'ExecStart', u'value': u'/usr/bin/sleep 1d'}]}>
 
    # APIError raised for an invalid unit name
    >>> fleet_client.set_unit_desired_state('invalid-service', 'inactive')
    fleet.v1.errors.APIError: unit does not exist and options field empty (409)

    # ValueError raised for an invalid state
    >>> fleet_client.set_unit_desired_state('foo.service', 'invalid-state')
    ValueError: state must be one of: ['inactive', 'loaded', 'launched']


## destroy_unit()

Delete a unit from the cluster

### destroy_unit(self, unit)
* **unit (str, [Unit](unit.md)):** The Unit, or name of the unit to delete

### Returns
* **True:** The unit was deleted

### Raises
* [APIError](apierror.md): Fleet returned a response code >= 400

### Example

    # delete by passing the unit
    >>> fleet_client.destroy_unit(unit)
    True

    # or it's name
    >>> fleet_client.destroy_unit('foo.service')
    True
 
    # APIError is raised if the unit does not exist
    >>> fleet_client.destroy_unit('invalid-service')
    fleet.v1.errors.APIError: unit does not exist (404)

## list_units()

Returns a generator that yields each [Unit](unit.md) in the cluster

### list_units(self):

### Yields:
* [Unit](unit.md): The next Unit in the cluster

### Raises
* [APIError](apierror.md): Fleet returned a response code >= 400

### Example

    >>> for unit in fleet_client.list_units():
    ...     unit
    ... 
    <Unit: {u'machineID': u'2901a44df0834bef935e24a0ddddcc23', u'desiredState': u'launched', u'options': [{u'section': u'Service', u'name': u'ExecStart', u'value': u'/usr/bin/sleep 1d'}], u'currentState': u'launched', u'name': u'foo.service'}>

## get_unit()
 
Retreive a specific [Unit](unit.md) from the cluster by name.

### get_unit(self, name)
* **name (str):** If specified, only this unit name is returned

### Returns
* [Unit](unit.md): The unit identified by ``name``

### Raises
* [APIError](apierror.md): Fleet returned a response code >= 400

### Example

    # get a service by name
    >>> fleet_client.get_unit('foo.service')
    <Unit: {u'machineID': u'2901a44df0834bef935e24a0ddddcc23', u'desiredState': u'launched', u'options': [{u'section': u'Service', u'name': u'ExecStart', u'value': u'/usr/bin/sleep 1d'}], u'currentState': u'launched', u'name': u'foo.service'}>

    # APIError raised for invalid service names
    >>> fleet_client.get_unit('invalid-service')
    fleet.v1.errors.APIError: unit does not exist (404)


## list_unit_states()

Returns a generator tht yields the current [UnitState](unitstate.md) for each unit in the cluster
     
### list_unit_states(self, machine_id = None, unit_name = None)

* **machine_id (str):** filter all UnitState objects to those originating from a specific machine
* **unit_name (str):**  filter all UnitState objects to those related to a specific unit

### Yields
* [UnitState](unitstate.md): The next UnitState in the cluster

### Raises
* [APIError](apierror.md): Fleet returned a response code >= 400

### Example
    >>> for unit_state in fleet_client.list_unit_states():
    ...     unit_state
    ... 
    <UnitState: {"hash": "dd401fa78c2de99a9c4045cbb4b285679067acf6", "name": "foo.service", "machineID": "2901a44df0834bef935e24a0ddddcc23", "systemdSubState": "running", "systemdActiveState": "active", "systemdLoadState": "loaded"}>


## list_machines()

Return a generator that yields each [Machine](machine.md) in the cluster

### list_machines(self)

### Yields
* [Machine](machine.md): The next machine in the cluster

### Raises
* [APIError](apierror.md): Fleet returned a response code >= 400

### Example

    >>> for machine in fleet_client.list_machines():
    ...     machine
    ... 
    <Machine: {"primaryIP": "198.51.100.23", "id": "2901a44df0834bef935e24a0ddddcc23", "metadata": {}}>