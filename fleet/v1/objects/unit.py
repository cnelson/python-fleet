from .fleet_object import FleetObject

try:  # pragma: no cover
    # python 2
    from StringIO import StringIO
except ImportError:  # pragma: no cover
    # python 3
    from io import StringIO


class Unit(FleetObject):
    """This object represents a Unit in Fleet

    Create and modify Unit entities to communicate to fleet the desired state of the cluster.
    This simply declares what should be happening; the backend system still has to react to the changes in
    this desired state. The actual state of the system is communicated with UnitState entities.

    Attributes (all are readonly):
        Always available:
            options (update with add_option, remove_option): list of UnitOption entities
            desiredState: (update with set_desired_state): state the user wishes the Unit to be in
                          ("inactive", "loaded", or "launched")

        Available once units are submitted to fleet:
            name: unique identifier of entity
            currentState: state the Unit is currently in (same possible values as desiredState)
            machineID: ID of machine to which the Unit is scheduled

    A UnitOption represents a single option in a systemd unit file.
        section: name of section that contains the option (e.g. "Unit", "Service", "Socket")
        name: name of option (e.g. "BindsTo", "After", "ExecStart")
        value: value of option (e.g. "/usr/bin/docker run busybox /bin/sleep 1000")


    """

    _STATES = ['inactive', 'loaded', 'launched']

    def __init__(self, client=None, data=None, desired_state=None, options=None, from_file=None, from_string=None):
        """Create a new unit

        Args:
            client (fleet.v1.Client, optional): The fleet client that retrieved this object
            data (dict, optional): Initialize this object with this data.  If this is used you must not
                                   specify options, desired_state, from_file, or from_string

            desired_state (string, optional): The desired_state for this object, defaults to 'launched' if not specified

            If you do not specify data, You may specify one of the following args to initialize the object:

                options (list, optional): A list of options to initialize the object with.
                from_file (str, optional): Initialize this object from the unit file on disk at this path
                from_string (str, optional): Initialize this object from the unit file in this string

                If none are specified, an empty unit will be created

        Raises:
            IOError: from_file was specified and it does not exist
            ValueError: Conflicting options, or The unit contents specified in from_string or from_file is not valid

        """

        # make sure if they specify data, then they didn't specify anything else
        if data and (desired_state or options or from_file or from_string):
            raise ValueError('If you specify data you can not specify desired_state,'
                             'options, from_file, or from_string')

        # count how many of options, from_file, from_string we have
        given = 0
        for thing in [options, from_file, from_string]:
            if thing:
                given += 1

        # we should only have one, if we have more, yell at them
        if given > 1:
            raise ValueError('You must specify only one of options, from_file, from_string')

        # ensure we have a minimum structure if we aren't passed one
        if data is None:

            # we set this here, instead as a default value to the arg
            # as we want to be able to check it vs data above, it should be None in that case
            if desired_state is None:
                desired_state = 'launched'

            if options is None:
                options = []

            # Minimum structure required by fleet
            data = {
                'desiredState': desired_state,
                'options': options
            }

        # Call the parent class to configure us
        super(Unit, self).__init__(client=client, data=data)

        # If they asked us to load from a file, attemp to slurp it up
        if from_file:
            with open(from_file, 'r') as fh:
                self._set_options_from_file(fh)

        # If they asked us to load from a string, lie to the loader with StringIO
        if from_string:
            self._set_options_from_file(StringIO(from_string))

    def __repr__(self):
        return '<{0}: {1}>'.format(
            self.__class__.__name__,
            self.as_dict()
        )

    def __str__(self):
        """Generate a Unit file representation of this object"""

        # build our output here
        output = []

        # get a ist of sections
        sections = set([x['section'] for x in self._data['options']])

        for section in sections:
            # for each section, add it to our output
            output.append(u'[{0}]'.format(section))

            # iterate through the list of options, adding all items to this section
            for option in self._data['options']:
                if option['section'] == section:
                    output.append(u'{0}={1}'.format(option['name'], option['value']))

        # join and return the output
        return u"\n".join(output)

    def _set_options_from_file(self, file_handle):
        """Parses a unit file and updates self._data['options']

        Args:
            file_handle (file): a file-like object (supporting read()) containing a unit

        Returns:
            True: The file was successfuly parsed and options were updated

        Raises:
            IOError: from_file was specified and it does not exist
            ValueError: The unit contents specified in from_string or from_file is not valid
        """

        # TODO: Find a library to handle this unit file parsing
        # Can't use configparser, it doesn't handle multiple entries for the same key in the same sectoin
        # This is terribly naive

        # build our output here
        options = []

        # keep track of line numbers to report when parsing problems happen
        line_number = 0

        # the section we are currently in
        section = None
        for line in file_handle.read().splitlines():
            line_number += 1

            # clear any extra white space
            line = line.strip()

            # ignore comments, and blank lines
            if not line or line.startswith('#'):
                continue

            # is this a section header?  If so, update our variable and continue
            # Section headers look like: [Section]
            if line.startswith('[') and line.endswith(']'):
                section = line.strip('[]')
                continue

            # We encountered a non blank line outside of a section, this is a problem
            if not section:
                raise ValueError(
                    'Unable to parse unit file; '
                    'Unexpected line outside of a section: {0} (line: {1}'.format(
                        line,
                        line_number
                    ))

            # Attempt to parse a line inside a section
            # Lines should look like: name=value
            try:
                name, value = line.split('=', 1)
                options.append({
                    'section': section,
                    'name': name,
                    'value': value
                })
            except ValueError:
                raise ValueError(
                    'Unable to parse unit file; '
                    'Malformed line in section {0}: {1} (line: {2}'.format(
                        section,
                        line,
                        line_number
                    ))

        # update our internal structure
        self._data['options'] = options

        return True

    def _is_live(self):
        """Checks to see if this unit came from fleet, or was created locally

        Only units with a .name property (set by the server), and _client property are considered 'live'

        Returns:
            True: The object is live
            False: The object is not

        """
        if 'name' in self._data and self._client:
            return True

        return False

    def add_option(self, section, name, value):
        """Add an option to a section of the unit file

        Args:
            section (str): The name of the section, If it doesn't exist it will be created
            name (str): The name of the option to add
            value (str): The value of the option

        Returns:
            True: The item was added

        """

        # Don't allow updating units we loaded from fleet, it's not supported
        if self._is_live():
            raise RuntimeError('Submitted units cannot update their options')

        option = {
            'section': section,
            'name': name,
            'value': value
        }

        self._data['options'].append(option)

        return True

    def remove_option(self, section, name, value=None):
        """Remove an option from a unit

        Args:
            section (str): The section to remove from.
            name (str): The item to remove.
            value (str, optional): If specified, only the option matching this value will be removed
                                   If not specified, all options with ``name`` in ``section`` will be removed

        Returns:
            True: At least one item was removed
            False: The item requested to remove was not found

        """
        # Don't allow updating units we loaded from fleet, it's not supported
        if self._is_live():
            raise RuntimeError('Submitted units cannot update their options')

        removed = 0
        # iterate through a copy of the options
        for option in list(self._data['options']):
            # if it's in our section
            if option['section'] == section:
                # and it matches our name
                if option['name'] == name:
                    # and they didn't give us a value, or it macthes
                    if value is None or option['value'] == value:
                        # nuke it from the source
                        self._data['options'].remove(option)
                        removed += 1

        if removed > 0:
            return True

        return False

    def destroy(self):
        """Remove a unit from the fleet cluster

        Returns:
            True: The unit was removed

        Raises:
            fleet.v1.errors.APIError: Fleet returned a response code >= 400

        """

        # if this unit didn't come from fleet, we can't destroy it
        if not self._is_live():
            raise RuntimeError('A unit must be submitted to fleet before it can destroyed.')

        return self._client.destroy_unit(self.name)

    def set_desired_state(self, state):
        """Update the desired state of a unit.

        Args:
            state (str): The desired state for the unit, must be one of ``_STATES``

        Returns:
            str: The updated state

         Raises:
            fleet.v1.errors.APIError: Fleet returned a response code >= 400
            ValueError: An invalid value for ``state`` was provided
        """
        if state not in self._STATES:
            raise ValueError(
                'state must be one of: {0}'.format(
                    self._STATES
                ))

        # update our internal structure
        self._data['desiredState'] = state

        # if we have a name, then we came from the server
        # and we have a handle to an active client
        # Then update our selves on the server
        if self._is_live():
            self._update('_data', self._client.set_unit_desired_state(self.name, self.desiredState))

        # Return the state
        return self._data['desiredState']
