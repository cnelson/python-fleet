from .fleet_object import FleetObject


class Machine(FleetObject):
    """A Machine represents a host in the cluster. It uses the host's machine-id as a unique identifier.

    Attribues:
        id: unique identifier of Machine entity
        primaryIP: IP address that should be used to communicate with this host
        metadata: dictionary of key-value data published by the machine
    """

    def __init__(self, client=None, data=None):
        # fleet api doesn't return a key for metadata if there is none
        # we want to retun an empty dict in those cases for consistency
        if 'metadata' not in data:
            data['metadata'] = {}

        super(Machine, self).__init__(client=client, data=data)
