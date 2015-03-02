# python-fleet

A python client for [fleet](https://github.com/coreos/fleet)
## Install


### Install from PyPI
    
    $ pip install fleet


### Install from source
    
    $ git clone https://github.com/cnelson/python-fleet
    $ cd python-fleet && python setup.py install


## Quick Start

This is a high-level overview of python-fleet's interface. For full documentation on all methods, see the documentation for individual classes.


### Importing fleet

Always import the specific version you wish to use. Currently 'v1' is supported.

    import fleet.v1 as fleet


### Error handling

All methods except for the constructor can raise an [APIError](apierror.md) if fleet responds with an error.  

Developers must catch and handle these exceptions.  Do not ignore errors.

### Create a client

The [fleet API documentation](https://github.com/coreos/fleet/blob/master/Documentation/api-v1.md#capability-discovery) states that clients should generate their bindings using the [discovery document](https://developers.google.com/discovery/v1/reference/apis) fleet provides.

python-fleet will attempt to retrieve and parse this document when it is instantiated.  Should any error occur during this process ``ValueError`` will be raised.

    from __future__ import print_function

    # connect to fleet over tcp
    try:
        fleet_client = fleet.Client('http://127.0.0.1:49153')
    except ValueError as exc:
        print('Unable to discover fleet: {0}'.format(exc))
        raise SystemExit

    # or over a unix domain socket
    try:
        fleet_client = fleet.Client('http+unix://%2Fvar%2Frun%2Ffleet.sock')
    except ValueError as exc:
        print('Unable to discover fleet: {0}'.format(exc))
        raise SystemExit

### Create a unit


Fleet units can be created in several different ways. See the [Unit](unit.md) documenation for full explanations of each option


#### Instantiate and manually add options

    unit = fleet.Unit()
    unit.add_option('Service', 'ExecStart', '/usr/bin/sleep 1d')

#### From an existing list of options

    unit = fleet.Unit(options=[{'section': 'Service', 'name': 'ExecStart', 'value': '/usr/bin/sleep 1d'}])
    
#### From a string containing a unit file

    unit = fleet.Unit(from_string="[Service]\nExecStart=/usr/bin/sleep1d")

#### From a file

    unit = fleet.Unit(from_file='/path/to/foo.service')

Once the unit object has been created, pass it to the ``create_unit`` method to submit the unit to the fleet cluster

    try:
        unit = fleet_client.create_unit('foo.service', unit)
    except fleet.APIError as exc:
        print('Unable to create unit: {0}'.format(exc))
        raise SystemExit


### Modify a Unit's desiredState
    
Once a unit has been submited to the cluster, the only writable field is ``desiredState``.

To update a unit's desired state call the ``set_desired_state`` method.


    try:
        unit.set_desired_state('inactive')
    except fleet.APIError as exc:
        print('Unable to modify unit: {0}'.format(exc))
        raise SystemExit

### List Units

Returns a generator that yields each [Unit](unit.md) in the cluster

    try:
        for unit in fleet.list_units():
            print(unit)
    except fleet.APIError as exc:
        print('Unable to list units: {0}'.format(exc))
        raise SystemExit


### Get a Unit

Retreive a specific [Unit](unit.md) from the cluster by name.

If the unit is not found, [APIError](apierror.md) will be raised with code == 404

    try:
        unit = fleet.get_unit('foo.service')
    except fleet.APIError as exc:
        if exc.code == 404:
            print('Unit foo.service does not exist.')
        else:
            print('Unable to get unit: {0}'.format(exc))

### List Current Unit State

Returns a generator tht yields the current [UnitState](unitstate.md) for each unit in the cluster

See the [fleet API documention's section on UnitState](https://github.com/coreos/fleet/blob/master/Documentation/api-v1.md#current-unit-state) for information on the difference between Unit and UnitState

    try:
        for unit_state in fleet.list_unit_states():
            print(unit_state)
    except fleet.APIError as exc:
        print('Unable to list unit state: {0}'.format(exc))
        raise SystemExit

### List Machines

Return a generator that yields each [Machine](machine.md) in the cluster

    try:
        for machine in fleet.list_machines():
            print(machine)
    except fleet.APIError as exc:
        print('Unable to list machines: {0}'.format(exc))
        raise SystemExit