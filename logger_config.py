# python module for setting up a logger with optional file output and console output
import logging

# name is the name of the logger,
# log_file is the file to write logs to (if None, logs will be printed to console),
# log_level is the logging level (default is INFO)
def setup_logger(
    name="app_logger",
    log_file=None,
    log_level=logging.INFO,
    output_mode="console",
):
    """
    Configure and return a logger.

    output_mode options:
    - "console" -> show logs in terminal
    - "file"    -> write logs to a file only
    - "both"    -> console and file
    - "silent"  -> no output
    """

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s | %(lineno)d | %(message)s"
    )

    if output_mode == "silent":
        logger.addHandler(logging.NullHandler())
        return logger

    if output_mode in ("console", "both"):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if output_mode in ("file", "both"):
        if not log_file:
            raise ValueError("log_file is required when output_mode is 'file' or 'both'.")

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger