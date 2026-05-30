import logging

from api_testing.utils import log as log_utils


def test_suppress_console_logging_does_not_silence_file_handler(tmp_path):
    logger = log_utils.configure_logging(
        class_name="test_logger",
        log_dir=tmp_path,
        llm_model="unit-test",
        level=logging.DEBUG,
        console_level=logging.INFO,
    )

    console_handlers = [
        handler
        for handler in logger.handlers
        if type(handler) is logging.StreamHandler
    ]
    file_handlers = [
        handler for handler in logger.handlers if isinstance(handler, logging.FileHandler)
    ]

    assert console_handlers, "Expected at least one console handler"
    assert file_handlers, "Expected at least one file handler"

    log_utils.suppress_console_logging()

    assert console_handlers[0].level == logging.CRITICAL + 1
    assert file_handlers[0].level == logging.DEBUG
