import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def format_datetime(dt: datetime, fmt: str) -> str:
    """Format datetime with error handling."""
    try:
        return dt.strftime(fmt)
    except (ValueError, TypeError) as e:
        logger.warning(f"Error formatting datetime {dt}: {e}")
        return dt.isoformat()
