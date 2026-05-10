import logging
import os

logger = None
_log_dir = "./logs"
_log_level = logging.DEBUG
_log_llm_model = 'default'
_console_level = logging.INFO

def getLogger(name: str|None = None):
    global logger
    if logger is None:
        return configure_logging(name)
    if name:
        logger.name = name
    return logger

def configure_logging(class_name: str = __name__, log_dir=None, level=None, llm_model=None, console_level=None):
    global logger, _log_dir, _log_level, _log_llm_model, _console_level
    log_dir = os.path.join(log_dir, "logs") if log_dir else _log_dir
    level = level or _log_level
    llm_model = llm_model or _log_llm_model
    console_level = console_level or _console_level

    os.makedirs(log_dir, exist_ok=True)

    if logger is not None:
        for handler in logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.close()
            logger.remove_handler(handler)

    log = logging.getLogger(class_name)
    log.setLevel(level)
    log.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(console_level)
    log.addHandler(console_handler)

    log_path = os.path.join(log_dir, f"{llm_model}.log")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    log.addHandler(file_handler)

    logger = log
    return logger

def set_console_level(level: int):
    global _console_level, logger
    _console_level = level
    if logger:
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(level)

def suppress_console_logging():
    set_console_level(logging.CRITICAL + 1)

def restore_console_logging(level: int = logging.INFO):
    set_console_level(level)
