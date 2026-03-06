"""Location normalization and geocoding (SPEC.md §3.4).

Handles 10 location patterns. Geocoding priority:
1. Adzuna: use provided lat/lon directly
2. Extract UK postcode → postcodes.io
3. City/town → postcodes.io places or fallback table
4. No geocoding possible → set type from keywords
"""

import re

import httpx
import structlog

logger = structlog.get_logger()

# UK full postcode pattern
_POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b", re.IGNORECASE)

# UK outcode pattern (first part only)
_OUTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?)\b", re.IGNORECASE)

# Location type keywords
_REMOTE_RE = re.compile(r"\b(?:remote|work\s*from\s*home|wfh)\b", re.IGNORECASE)
_HYBRID_RE = re.compile(r"\bhybrid\b", re.IGNORECASE)
_NATIONWIDE_RE = re.compile(
    r"\b(?:various\s*locations|nationwide|multiple\s*locations|UK[\s-]*wide)\b",
    re.IGNORECASE,
)
_NEAR_RE = re.compile(r"\bnear\s+", re.IGNORECASE)

# Well-known London areas
_LONDON_AREAS: dict[str, tuple[float, float]] = {
    "central london": (51.5074, -0.1278),
    "city of london": (51.5155, -0.0922),
    "east london": (51.5311, -0.0481),
    "west london": (51.5074, -0.2284),
    "north london": (51.5616, -0.1026),
    "south london": (51.4620, -0.1150),
}

# Default coordinates for London
_LONDON_DEFAULT = (51.5074, -0.1278)

# Postcodes.io endpoints
POSTCODES_BULK_URL = "https://api.postcodes.io/postcodes"
POSTCODES_PLACES_URL = "https://api.postcodes.io/places"
POSTCODES_OUTCODES_URL = "https://api.postcodes.io/outcodes"


class LocationResult:
    """Result of location normalization."""

    def __init__(
        self,
        city: str | None = None,
        region: str | None = None,
        postcode: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        location_type: str = "onsite",
    ) -> None:
        self.city = city
        self.region = region
        self.postcode = postcode
        self.latitude = latitude
        self.longitude = longitude
        self.location_type = location_type


def detect_location_type(text: str) -> str:
    """Detect location type from text keywords."""
    if _REMOTE_RE.search(text):
        return "remote"
    if _HYBRID_RE.search(text):
        return "hybrid"
    if _NATIONWIDE_RE.search(text):
        return "nationwide"
    return "onsite"


def extract_postcode(text: str) -> str | None:
    """Extract UK postcode from text."""
    match = _POSTCODE_RE.search(text)
    if match:
        return match.group(1).upper()
    return None


def _clean_location_text(text: str) -> str:
    """Clean location text: strip type prefixes, 'near', etc."""
    # Remove "Hybrid - ", "Remote - " prefixes
    cleaned = re.sub(
        r"^(?:hybrid|remote|onsite)\s*[-–—:]\s*", "", text, flags=re.IGNORECASE
    )
    # Remove "near"
    cleaned = _NEAR_RE.sub("", cleaned)
    return cleaned.strip()


async def geocode_postcode(
    postcode: str,
    client: httpx.AsyncClient | None = None,
) -> tuple[float, float] | None:
    """Geocode a UK postcode via postcodes.io."""
    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=10.0)
        should_close = True
    try:
        resp = await client.post(
            POSTCODES_BULK_URL,
            json={"postcodes": [postcode]},
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("result", [])
            if results and results[0].get("result"):
                r = results[0]["result"]
                return (float(r["latitude"]), float(r["longitude"]))
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        logger.warning("postcodes_io_error", postcode=postcode)
    finally:
        if should_close:
            await client.aclose()
    return None


async def geocode_place(
    place_name: str,
    client: httpx.AsyncClient | None = None,
) -> tuple[float, float, str | None] | None:
    """Geocode a place name via postcodes.io places endpoint.

    Returns (lat, lon, region) or None.
    """
    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=10.0)
        should_close = True
    try:
        resp = await client.get(
            POSTCODES_PLACES_URL,
            params={"q": place_name, "limit": "1"},
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("result", [])
            if results:
                r = results[0]
                lat = float(r["latitude"])
                lon = float(r["longitude"])
                region = r.get("region")
                return (lat, lon, region)
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        logger.warning("postcodes_io_places_error", place=place_name)
    finally:
        if should_close:
            await client.aclose()
    return None


async def normalize_location(
    location_raw: str,
    latitude: float | None = None,
    longitude: float | None = None,
    source_name: str = "",
    uk_cities: dict[str, tuple[float, float, str]] | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> LocationResult:
    """Normalize location string to structured fields.

    Args:
        location_raw: Raw location text from job listing.
        latitude: Pre-provided lat (e.g. from Adzuna).
        longitude: Pre-provided lon (e.g. from Adzuna).
        source_name: Source API name.
        uk_cities: Fallback city table {name_lower: (lat, lon, region)}.
        http_client: Shared httpx client for postcodes.io calls.
    """
    if not location_raw:
        return LocationResult()

    result = LocationResult()

    # Detect type first
    result.location_type = detect_location_type(location_raw)

    # Remote: no geometry needed
    if result.location_type == "remote":
        return result

    # Nationwide: no geometry
    if result.location_type == "nationwide":
        return result

    # Priority 1: Adzuna provides lat/lon directly (skip postcodes.io)
    if latitude is not None and longitude is not None:
        result.latitude = latitude
        result.longitude = longitude
        # Try to get city from text
        cleaned = _clean_location_text(location_raw)
        if cleaned:
            result.city = cleaned.split(",")[0].strip()
        return result

    # Clean the text for geocoding
    cleaned = _clean_location_text(location_raw)
    if not cleaned:
        return result

    cleaned_lower = cleaned.lower().strip()

    # Priority 2: Extract UK postcode
    postcode = extract_postcode(location_raw)
    if postcode:
        result.postcode = postcode
        coords = await geocode_postcode(postcode, http_client)
        if coords:
            result.latitude, result.longitude = coords
            return result

    # Check London special cases
    if cleaned_lower in _LONDON_AREAS:
        lat, lon = _LONDON_AREAS[cleaned_lower]
        result.latitude = lat
        result.longitude = lon
        result.city = "London"
        result.region = "Greater London"
        return result

    if cleaned_lower == "london" or cleaned_lower.startswith("london "):
        # Check for outcode like "London EC2"
        parts = cleaned.split()
        if len(parts) > 1:
            outcode = parts[-1].upper()
            # Try postcodes.io outcodes
            if http_client:
                try:
                    resp = await http_client.get(f"{POSTCODES_OUTCODES_URL}/{outcode}")
                    if resp.status_code == 200:
                        data = resp.json()
                        r = data.get("result", {})
                        if r:
                            result.latitude = float(r["latitude"])
                            result.longitude = float(r["longitude"])
                            result.city = "London"
                            result.region = "Greater London"
                            return result
                except (httpx.HTTPError, KeyError, TypeError, ValueError):
                    pass

        # Default London
        result.latitude, result.longitude = _LONDON_DEFAULT
        result.city = "London"
        result.region = "Greater London"
        return result

    # Check UK regions (no geometry)
    _UK_REGIONS = {
        "south east",
        "south west",
        "north east",
        "north west",
        "east midlands",
        "west midlands",
        "east of england",
        "yorkshire",
        "yorkshire and the humber",
        "scotland",
        "wales",
        "northern ireland",
    }
    if cleaned_lower in _UK_REGIONS:
        result.region = cleaned
        return result

    # Priority 3: City lookup via postcodes.io places
    if http_client:
        place_result = await geocode_place(cleaned, http_client)
        if place_result:
            result.latitude, result.longitude = place_result[0], place_result[1]
            result.region = place_result[2]
            result.city = cleaned.split(",")[0].strip()
            return result

    # Priority 4: Fallback to pre-populated city table
    if uk_cities:
        city_key = cleaned_lower.split(",")[0].strip()
        if city_key in uk_cities:
            lat, lon, region = uk_cities[city_key]
            result.latitude = lat
            result.longitude = lon
            result.region = region
            result.city = cleaned.split(",")[0].strip()
            return result

    # No geocoding possible — preserve the raw text
    result.city = cleaned.split(",")[0].strip() if cleaned else None
    return result
