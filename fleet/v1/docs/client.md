# Client

A python wrapper for the [fleet v1 API](https://github.com/coreos/fleet/blob/master/Documentation/api-v1.md).

    >>> import fleet.v1 as fleet

    # connect over tcp
    >>> fleet_client = fleet.Client('http://127.0.0.1:49153')

    # or over a unix domain socket
    >>> fleet_client = fleet.Client('http+unix://%2Fvar%2Frun%2Ffleet.sock')

    # via an ssh tunnel
    >>> fleet_client = fleet.Client('http://127.0.0.1:49153', ssh_tunnel='198.51.100.23:22')

### Client(self, endpoint, http=None, ssh_tunnel=None, ssh_username='core', ssh_timeout=10, ssh_known_hosts_file='~/.fleetctl/known_hosts', ssh_strict_host_key_checking=True, ssh_raw_transport=None)

Connect to the fleet API and generate a client based on it's [discovery document](https://developers.google.com/discovery/v1/reference/apis?hl=en).

### Arguments

* **endpoint (str):**  A URL where the fleet API can be reached.  Supported schemes are:
    * **http:** A HTTP connection over a TCP socket.  ``http://127.0.0.1:49153``
    * **http+unix:** A HTTP connection over a unix domain socket. You must escape the path (/ = %2F). ``http+unix://%2Fvar%2Frun%2Ffleet.sock``

* **http (httplib2.Http):** An instance of httplib2.Http (or something that acts like it) that HTTP requests will be made through. You do not need to pass this unless you need to configure specific options for your http client, or want to pass in a mock for testing.

* **ssh_tunnel (str '\<host\>[:\<port\>]'):** Establish an SSH tunnel through the provided address for communication with fleet. Defaults to None. If specified, the following other options adjust it's behaivor:
    * **ssh_username (str):** Username to use when connecting to SSH, defaults to 'core'.
    * **ssh_timeout (float):** Amount of time in seconds to allow for SSH connection initialization before failing, defaults to 10.
    * **ssh_known_hosts_file (str):** File used to store remote machine fingerprints, defaults to '~/.fleetctl/known_hosts'.  Ignored if `ssh_strict_host_key_checking` is False
    * **ssh_strict_host_key_checking (bool):** Verify host keys presented by remote machines before initiating SSH connections, defaults to True.

* **ssh_raw_transport ([paramiko.transport.Transport](http://docs.paramiko.org/en/stable/api/transport.html#paramiko.transport.Transport)):** An active Transport on which [open_channel()](http://docs.paramiko.org/en/stable/api/transport.html#paramiko.transport.Transport.open_channel) will be called to establish connections. See [Advanced SSH Tunneling](#advanced-ssh-tunneling) for more information.

### Raises
* **ValueError:** The endpoint provided was not accessible.

### Advanced SSH Tunneling

If your ssh connection requires complex configuration, you can configure and [connect()](http://docs.paramiko.org/en/stable/api/client.html#paramiko.client.SSHClient.connect) your own [paramiko.client.Client](http://docs.paramiko.org/en/stable/api/client.html) and pass the result of [get_transport()](http://docs.paramiko.org/en/stable/api/client.html#paramiko.client.SSHClient.get_transport) as `ssh_raw_transport`

If `ssh_raw_transport` is set all other ssh options are ignored, it's assumed the caller will have fully configured and connected their ssh transport before invoking us.

    # example of configuring and connecting your own ssh client
    # this contrived example uses a specific key, 
    # and disables the use of the agent

    import fleet.v1 as fleet
    import paramiko

    # configure our client
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # connect to the host with our custom configuration
    ssh_client.connect(
        hostname='198.51.100.23',
        username='core', 
        key_filename='/tmp/the.key',
        allow_agent=False,
        look_for_keys=False
    )

    # pass the transport to the client
    fleet_client = fleet.Client(
        'http://127.0.0.1:49153', 
        ssh_raw_transport=ssh_client.get_transport()
    )


## Methods


## create_unit() 
Create a new [Unit](unit.md) in the cluster

    >>> fleet_client.create_unit('foo.service', fleet.Unit(from_file='foo.service'))
    <Unit: {u'desiredState': u'launched', u'name': u'foo.service', u'currentState': u'inactive', u'options': [{u'section': u'Service', u'name': u'ExecStart', u'value': u'/usr/bin/sleep 1d'}]}>

### create_unit(self, name, unit)
* **name (str):** The name of the unit to create
* **unit ([Unit](unit.md)):** The unit to submit to fleet 

### Returns
* [Unit](unit.md): The unit that was created

### Raises
* [APIError](apierror.md): Fleet returned a response code >= 400


## set_unit_desired_state()

Update the desired state of a unit running in the cluster.

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

### set_unit_desired_state(self, unit, desired_state)
* **unit (str, [Unit](unit)):** The Unit, or name of the unit to delete
* **desired_state (str)**: State the user wishes the Unit to be in  ("inactive", "loaded", or "launched")

### Returns
* [Unit](unit.md): The updated unit

### Raises
* [APIError](apierror.md): Fleet returned a response code >= 400
* **ValueError:** An invalid value was provided for ``desired_state``

## destroy_unit()

Delete a unit from the cluster

    # delete by passing the unit
    >>> fleet_client.destroy_unit(unit)
    True

    # or it's name
    >>> fleet_client.destroy_unit('foo.service')
    True
 
    # APIError is raised if the unit does not exist
    >>> fleet_client.destroy_unit('invalid-service')
    fleet.v1.errors.APIError: unit does not exist (404)


### destroy_unit(self, unit)
* **unit (str, [Unit](unit.md)):** The Unit, or name of the unit to delete

### Returns
* **True:** The unit was deleted

### Raises
* [APIError](apierror.md): Fleet returned a response code >= 400

## list_units()

Returns a generator that yields each [Unit](unit.md) in the cluster


    >>> for unit in fleet_client.list_units():
    ...     unit
    ... 
    <Unit: {u'machineID': u'2901a44df0834bef935e24a0ddddcc23', u'desiredState': u'launched', u'options': [{u'section': u'Service', u'name': u'ExecStart', u'value': u'/usr/bin/sleep 1d'}], u'currentState': u'launched', u'name': u'foo.service'}>

### list_units(self):

### Yields:
* [Unit](unit.md): The next Unit in the cluster

### Raises
* [APIError](apierror.md): Fleet returned a response code >= 400


## get_unit()
 
Retreive a specific [Unit](unit.md) from the cluster by name.

    # get a service by name
    >>> fleet_client.get_unit('foo.service')
    <Unit: {u'machineID': u'2901a44df0834bef935e24a0ddddcc23', u'desiredState': u'launched', u'options': [{u'section': u'Service', u'name': u'ExecStart', u'value': u'/usr/bin/sleep 1d'}], u'currentState': u'launched', u'name': u'foo.service'}>

    # APIError raised for invalid service names
    >>> fleet_client.get_unit('invalid-service')
    fleet.v1.errors.APIError: unit does not exist (404)

### get_unit(self, name)
* **name (str):** If specified, only this unit name is returned

### Returns
* [Unit](unit.md): The unit identified by ``name``

### Raises
* [APIError](apierror.md): Fleet returned a response code >= 400


## list_unit_states()

Returns a generator that yields the current [UnitState](unitstate.md) for each unit in the cluster

    >>> for unit_state in fleet_client.list_unit_states():
    ...     unit_state
    ... 
    <UnitState: {"hash": "dd401fa78c2de99a9c4045cbb4b285679067acf6", "name": "foo.service", "machineID": "2901a44df0834bef935e24a0ddddcc23", "systemdSubState": "running", "systemdActiveState": "active", "systemdLoadState": "loaded"}>
    
 
### list_unit_states(self, machine_id = None, unit_name = None)

* **machine_id (str):** filter all UnitState objects to those originating from a specific machine
* **unit_name (str):**  filter all UnitState objects to those related to a specific unit

### Yields
* [UnitState](unitstate.md): The next UnitState in the cluster

### Raises
* [APIError](apierror.md): Fleet returned a response code >= 400


## list_machines()

Return a generator that yields each [Machine](machine.md) in the cluster


    >>> for machine in fleet_client.list_machines():
    ...     machine
    ... 
    <Machine: {"primaryIP": "198.51.100.23", "id": "2901a44df0834bef935e24a0ddddcc23", "metadata": {}}>

### list_machines(self)

### Yields
* [Machine](machine.md): The next machine in the cluster

### Raises
* [APIError](apierror.md): Fleet returned a response code >= 400
