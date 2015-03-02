from .fleet_object import FleetObject


class UnitState(FleetObject):
    """Whereas Unit entities represent the desired state of units known by fleet,
    UnitStates represent the current states of units actually running in the cluster.

    The information reported by UnitStates will not always align perfectly with the Units,
    as there is a delay between the declaration of desired state and the backend system making
    all of the necessary changes.

    Attributes:
        name: unique identifier of entity
        hash: SHA1 hash of underlying unit file
        machineID: ID of machine from which this state originated
        systemdLoadState: load state as reported by systemd
        systemdActiveState: active state as reported by systemd
        systemdSubState: sub state as reported by systemd
    """
    pass
