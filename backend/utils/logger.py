import sys
from loguru import logger

def setup_logging(log_level: str = "INFO", log_format: str = "json"):
    logger.remove() # Remove default handler

    if log_format == "json":
        logger.add(
            sys.stderr,
            level=log_level,
            format="{message}",
            serialize=True,
            enqueue=True # Use a queue for non-blocking logging
        )
        logger.add(
            "logs/file.json",
            rotation="10 MB", # Rotate file every 10 MB
            compression="zip", # Compress old log files
            level=log_level,
            format="{message}",
            serialize=True,
            enqueue=True
        )
    elif log_format == "csv":
        # For CSV, we'll log a simpler format and assume structured data is handled elsewhere
        logger.add(
            sys.stderr,
            level=log_level,
            format="<green>{time}</green> <level>{level}</level> <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            enqueue=True
        )
        logger.add(
            "logs/file.csv",
            rotation="10 MB",
            compression="zip",
            level=log_level,
            format="{time},{level},{message}", # Simple CSV format
            enqueue=True
        )
    else:
        logger.add(
            sys.stderr,
            level=log_level,
            format="<green>{time}</green> <level>{level}</level> <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            enqueue=True
        )
        logger.warning(f"Unknown log format '{log_format}'. Falling back to default text format.")

    return logger