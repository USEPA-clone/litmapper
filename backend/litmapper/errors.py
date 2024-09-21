class ResourceCreationInProgress(Exception):
    """
    Exception to be raised when a database query determines the object
    is still being created.
    """


class ResourceDoesNotExist(Exception):
    """
    Exception to be raised when a database query determines the object
    doesn't exist yet.
    """


class ResourceExists(Exception):
    """
    Exception to be raised when a database query determines an object
    already exists.
    """
