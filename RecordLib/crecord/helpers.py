from typing import Union
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


def convert_datestring(datestring: Union[str, date, datetime, None]) -> date:
    """
    Convert a datestring to a date
    """
    if datestring is None:
        return None
    if isinstance(datestring, date) or isinstance(datestring, datetime):
        return datestring
    for fmtstring in [r"%Y-%m-%d", r"%m/%d/%Y"]:
        try:
            return datetime.strptime(datestring, fmtstring).date()
        except:
            continue
    logger.error(f"Could not read date string: {datestring}")
    return None

