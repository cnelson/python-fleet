# APIError

This exception is raised whenever an error is returned in repsponse to a fleet API call

## Attributes
* **code (int):** The response code
* **message(str):** The message included with the error response
* **http_error([googleapiclient.errors.HttpError](http://google.github.io/google-api-python-client/docs/epy/googleapiclient.errors.HttpError-class.html)):** The underlying exception that caused this exception to be raised. If you need access to the raw response, this is where you'll find it.

## Example
	# attempting to retrieve an invalid unit, willl result in an APIError
	>>> fleet_client.get_unit('foo.service')
	fleet.v1.errors.APIError: unit does not exist (404)
