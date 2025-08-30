# --------------------------
# Helper functions
# --------------------------

def str_to_bool(var, value, logger=None):
    """
    Convert a string to boolean.

    Args:
        var (str): The name of the variable for logging purposes.
        value (str): The string to convert ('true'/'false').
        logger (logging.Logger, optional): Logger instance to use. Defaults to None.

    Returns:
        bool: True if value is 'true', False if value is 'false'.

    Raises:
        ValueError: If value is not 'true' or 'false'.
    """
    logger = logger or __import__('logging').getLogger()  # Use passed logger or root logger

    if value.lower() == 'true':
        return True
    elif value.lower() == 'false':
        return False
    else:
        logger.error(f"Invalid value for {var}: {value}")
        raise ValueError(f"Invalid value for {var}")
