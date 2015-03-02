class APIError(Exception):
    """Represents an error returned in a response to a fleet API call

    This exception will be raised any time a response code >= 400 is returned

    Attributes:
        code (int): The response code
        message(str): The message included with the error response
        http_error(googleapiclient.errors.HttpError): The underlying exception that caused this exception to be raised
                                                      If you need access to the raw response, this is where you'll find
                                                      it.
    """
    def __init__(self, code, message, http_error):
        """Construct an exception representing an error returned by fleet

        Args:
            code (int): The response code
            message(str): The message included with the error response
            http_error(googleapiclient.errors.HttpError): The underlying exception that caused this exception
                                                          to be raised.
        """

        self.code = code
        self.message = message
        self.http_error = http_error

    def __str__(self):
        # Return a string like r'Some bad thing happened(400)'
        return '{1} ({0})'.format(
            self.code,
            self.message
        )

    def __repr__(self):
        # Retun a string like r'<Fleetv1Error; Code: 400; Message: Some bad thing happened>'
        return '<{0}; Code: {1}; Message: {2}>'.format(
            self.__class__.__name__,
            self.code,
            self.message

        )
