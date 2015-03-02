# Unit

Create and modify Unit entities to communicate to fleet the desired state of the cluster.

This simply declares what *should* be happening; the backend system still has to react to the changes in this desired state.

The actual state of the system is communicated with [UnitState](unitstate.md) entities.

### Attributes
#### Always available
* **desiredState (str):** state the user wishes the Unit to be in ("inactive", "loaded", or "launched")
* **options (list of dicts):** list of UnitOption entities

#### Available once units are submitted to fleet
* **name**: (str) unique identifier of entity
* **currentState (str):** (readonly) state the Unit is currently in (same possible values as desiredState)
* **machineID (str):** ID of machine to which the Unit is scheduled

#### Unit Option

A UnitOption is a dict that represents a single option in a systemd unit file.  The dict must contain these three keys

* **section (str)**: name of section that contains the option (e.g. "Unit", "Service", "Socket")
* **name (str)**: name of option (e.g. "BindsTo", "After", "ExecStart")
* **value (str)**: value of option (e.g. "/usr/bin/docker run busybox /bin/sleep 1000")


## Attribute Access

You can access the attributes of this object as keys or attributes.

    >>> unit = fleet_client.list_units().next()
    >>> unit.name
    u'foo.service'
    >>> unit['name'] 
    u'foo.service'

## Unit Access

You can access the Unit as a [systemd unit configuration file](http://www.freedesktop.org/software/systemd/man/systemd.unit.html) by calling str() on the Unit

    >>> unit = fleet.Unit(options=[{'section': 'Service', 'name': 'ExecStart', 'value': '/usr/bin/sleep 1d'}])
    >>> str(unit)
    '[Service]\nExecStart=/usr/bin/sleep 1d'

## Creating Units

### Unit(desired_state='launched', options=None, from_file=None, from_string=None)
* **desired_state (string, optional):** The ``desiredState`` for this object, defaults to 'launched' if not specified
* **options (list, optional):** A list of options to initialize the object with.  
* **from_file (str, optional):** Initialize this object from the unit file on disk at this path
* **from_string (str, optional):** Initialize this object from the unit file in this string

If none are specified, an empty unit will be created

The use of ``options``, ``from_string``, and ``from_file`` parameters are mutually exclusive.


### Raises:
* **IOError**: ``from_file`` was specified and it does not exist
* **ValueError**: Conflicting options, or the unit contents specified in ``from_string`` or ``from_file`` is not valid

### Examples

### No initial state

When no parameters are given to the constructor, a blank unit is created.

You can use the ``.add_option`` method to furhter configure the unit.

    >>> unit = fleet.Unit()
    >>> unit
    <Unit: {'desiredState': 'launched', 'options': []}>


### Pass the options directly as a list of dicts

``options`` allows for the direct configuration of the unit.

    # sample option structure
    [
        {
            'section': 'Service', 
            'name': 'ExecStart', 
            'value': '/usr/bin/sleep 1d'
        }
    ]

This is a list of dicts, as returned by the fleet server.  Each dict must have three keys:
``section``, ``name``, and ``value``

    >>> unit = fleet.Unit(options=[{'section': 'Service', 'name': 'ExecStart', 'value': '/usr/bin/sleep 1d'}])
    >>> unit
    <Unit: {'desiredState': 'launched', 'options': [{'section': 'Service', 'name': 'ExecStart', 'value': '/usr/bin/sleep 1d'}]}>

### From a string containing a unit file

``from_string`` may be set to the contents of a [systemd unit configuration file](http://www.freedesktop.org/software/systemd/man/systemd.unit.html)

    >>> unit = fleet.Unit(from_string="[Service]\nExecStart=/usr/bin/sleep 1d")
    >>> unit
    <Unit: {'desiredState': 'launched', 'options': [{'section': 'Service', 'name': 'ExecStart', 'value': '/usr/bin/sleep 1d'}]}>

### From a file

``from_file`` may be set to the path to a [systemd unit configuration file](http://www.freedesktop.org/software/systemd/man/systemd.unit.html)

    >>> unit = fleet.Unit(from_file='/path/to/foo.service')
    >>> unit
    <Unit: {'desiredState': 'launched', 'options': [{'section': 'Service', 'name': 'ExecStart', 'value': '/usr/bin/sleep 1d'}]}>

### Desired State

    ``desired_state`` may be used in combination with the options listed above to set the unit's desired state when the object is initialized


## add_option()

Add an option to a section of the unit file

### add_option(section, name, value)
* **section (str)**: The name of the section, If it doesn't exist it will be created
* **name (str)**: The name of the option to add
* **value (str)**: The value of the option

### Returns:
* **True:** The item was added

### Raises
* **RuntimeError:** This method was called on a submitted unit.        

### Example:
    >>> unit = fleet.Unit()
    >>> unit.add_option('Service', 'ExecStart', '/usr/bin/sleep 1d')
    True


## remove_option()

Remove anoption from a unit


### remove_option(self, section, name, value=None):
* **section (str):** The section to remove from.
* **name (str):** The item to remove.
* **value (str, optional):** If specified, only the option matching this value will be removed.
If not specified, all options with ``name`` in ``section`` will be removed

### Returns:
* **True:** At least one item was removed
* **False:** The item requested to remove was not found

### Raises
* **RuntimeError:** This method was called on a submitted unit.        

### Example

    >>> unit = fleet.Unit()
    >>> unit.add_option('Service', 'ExecStart', '/usr/bin/sleep 1d')
    True
    >>> unit.remove_option('Service', 'ExecStart', 'foo')
    False
    >>> unit.remove_option('Service', 'ExecStart', '/usr/bin/sleep 1d')
    True

## set_desired_state()

Updates the ``desiredState`` for a unit.  If the unit was retrieved from a fleet cluster
It will attempt to update the status in the cluster when this method is called.


### set_desired_state(self, state):
* **state (str):** The desired state for the unit, must be one of: 'inactive', 'loaded', 'launched'

### Returns:
* **str:** The updated state

### Raises:
* [APIError](apierror.md): Fleet returned a response code >= 400     
* **ValueError:** An invalid value for ``state`` was provided       

### Example:

    # retrieve a unit from the cluster
    >>> unit = fleet_client.list_units().next()
    # update it
    >>> unit.set_desired_state('inactive')
    # an API request to fleet is made here
    u'inactive'

    # create a unit locally
    >>> unit = fleet.Unit()
    # update it
    >>> unit.set_desired_state('inactive')
    # no network request is made.
    'inactive'

    # attempt to use an invalue state value
    >>> unit.set_desired_state('invalid-state')
    ValueError: state must be one of: ['inactive', 'loaded', 'launched']


## destroy()

Remove a unit from the fleet cluster

### destroy(self):

### Returns:
* **True:** The unit was removed

### Raises:
* **[APIError](apierror.md):** Fleet returned a response code >= 400    
* **RuntimeError:** This method was called on a non-submitted unit.        

### Example:

    # submitted units come from a fleet cluster
    >>> unit = fleet_client.list_units().next()
    >>> unit.destroy()
    True

    # unsubmitted units are created locally and have not been sent to the cluster yet
    >>> unit = fleet.Unit()
    >>> unit.destroy()
    RuntimeError: A unit must be submitted to fleet before it can destroyed.

