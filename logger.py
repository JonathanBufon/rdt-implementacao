import logging
import os


def get_logger(router_id):
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger(f"router_{router_id}")
    if not logger.handlers:
        handler = logging.FileHandler(f"logs/router_{router_id}.log")
        fmt = logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger
