"""Constants for the LOE Lviv Outages integration."""

from typing import Final

DOMAIN: Final = "loe_lviv_outages"
NAME: Final = "LOE Lviv Outages"

# Configuration option
CONF_GROUP: Final = "group"

# Deprecated (for migration from Yasno)
CONF_REGION: Final = "region"
CONF_PROVIDER: Final = "provider"
CONF_CITY: Final = "city"
CONF_SERVICE: Final = "service"

# Consts
UPDATE_INTERVAL: Final = 15  # minutes

# Horizon constants for event lookahead
OUTAGE_LOOKAHEAD = 1  # day

# Values
STATE_NORMAL: Final = "normal"
STATE_OUTAGE: Final = "outage"

# Attribute keys
ATTR_EVENT_TYPE: Final = "event_type"
ATTR_EVENT_START: Final = "event_start"
ATTR_EVENT_END: Final = "event_end"

# Keys
TRANSLATION_KEY_EVENT_OUTAGE: Final = f"component.{DOMAIN}.common.electricity_outage"

# Text fallbacks
OUTAGE_TEXT_FALLBACK: Final = "Electricity Outage"

# Available groups
AVAILABLE_GROUPS: Final = [
    "1.1",
    "1.2",
    "2.1",
    "2.2",
    "3.1",
    "3.2",
    "4.1",
    "4.2",
    "5.1",
    "5.2",
    "6.1",
    "6.2",
]
