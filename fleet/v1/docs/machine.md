# Machine

A Machine represents a host in the cluster. It uses the host's [machine-id](http://www.freedesktop.org/software/systemd/man/machine-id.html) as a unique identifier.


## Attributes
* **id (str):** unique identifier of Machine
* **primaryIP (str):** IP address that should be used to communicate with this host
* **metadata (dict):** dictionary of key-value data published by the machine

## Attribute Access

You can access the attributes of this object as keys or attributes.

	>>> machine = fleet_client.list_machines().next()
	>>> machine.id
	u'2901a44df0834bef935e24a0ddddcc23'
	>>> machine['id']
	u'2901a44df0834bef935e24a0ddddcc23'
