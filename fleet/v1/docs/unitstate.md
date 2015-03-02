# UnitState

Whereas [Unit](unit.md) entities represent the desired state of units known by fleet, UnitStates represent the current states of units actually running in the cluster.

The information reported by UnitStates will not always align perfectly with the [Units](unit.md), as there is a delay between the declaration of desired state and the backend system making all of the necessary changes.

### Attributes

* **name (str)**: unique identifier of entity
* **hash (str)**: SHA1 hash of underlying unit file
* **machineID (str)**: ID of [machine](Machine) from which this state originated
* **systemdLoadState (str)**: load state as reported by systemd
* **systemdActiveState (str)**: active state as reported by systemd
* **systemdSubState (str)**: sub state as reported by systemd

## Attribute Access

You can access the attributes of this object as keys or attributes.

	>>> unitstate = fleet_client.list_unit_states().next()
	>>> unitstate.hash
	u'ffd74f8b9b1c4f7090928608308142f9'
	>>> unitstate['hash']
	u'ffd74f8b9b1c4f7090928608308142f9'
