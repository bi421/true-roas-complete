#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

from datetime import datetime
from zoneinfo import ZoneInfo


def get_us_now() -> datetime:
    """Returns the current time in Eastern Standard Time."""
    return datetime.now(ZoneInfo("America/New_York"))


def format_usd(amount: float) -> str:
    """Formats currency as $4,832.00."""
    return f"${amount:,.2f}"


def format_date_us(dt: datetime) -> str:
    """Formats dates as MM/DD/YYYY for US Compliance."""
    return dt.strftime("%m/%d/%Y")


def get_tax_deadline_status() -> bool:
    """Returns True if within 30 days of a US Tax Deadline."""
    now = get_us_now()
    deadlines = [datetime(now.year, 4, 15), datetime(now.year, 9, 15)]
    return any(0 <= (d.date() - now.date()).days <= 30 for d in deadlines)
