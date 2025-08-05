import logging
import sys
from app.core.config import settings

def setup_logging():
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

# Create and export a logger instance
logger = logging.getLogger(__name__)
