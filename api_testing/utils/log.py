import logging
import os

logger = None
_log_dir = "./logs"
_log_level = logging.DEBUG
_log_llm_model = 'default'

def getLogger(name: str|None = None):
    global logger
    if name:
        logger.name = name
    return logger

def configure_logging(class_name: str = __name__, log_dir=None, level=None, llm_model=None):
    
    global logger, _log_dir, _log_level, _log_llm_model
    log_dir = os.path.join(log_dir, "logs") if log_dir else _log_dir
    level = level or _log_level
    llm_model = llm_model or _log_llm_model
    print(f"Logging to {log_dir} at level {level} for model {llm_model}")
    os.makedirs(log_dir, exist_ok=True)
    log = logging.getLogger(class_name)
    log.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(level)
    log.addHandler(handler)

    # Define the log file path with TRACE_ID
    log_path = os.path.join(log_dir, f"{llm_model}.log")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")  # Create a file handler
    file_handler.setFormatter(formatter)  # Set the same formatter
    file_handler.setLevel(level)
    log.addHandler(file_handler)  # Add the file handler to the logger
    
    logger = log
    return logger
