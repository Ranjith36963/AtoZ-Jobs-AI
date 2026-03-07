"""Tests for location normalizer (SPEC.md §3.4, Gates P5–P8)."""

from unittest.mock import AsyncMock

import httpx
import pytest

from src.processing.location import (
    LocationResult,
    _clean_location_text,
    detect_location_type,
    extract_postcode,
    geocode_place,
    geocode_postcode,
    normalize_location,
)


class TestLocationTypeDetection:
    """Detect location type from text."""

    def test_remote(self) -> None:
        assert detect_location_type("Remote") == "remote"

    def test_wfh(self) -> None:
        assert detect_location_type("Work from home") == "remote"

    def test_hybrid(self) -> None:
        assert detect_location_type("Hybrid - Leeds") == "hybrid"

    def test_nationwide(self) -> None:
        assert detect_location_type("Various locations") == "nationwide"

    def test_uk_wide(self) -> None:
        assert detect_location_type("UK-wide") == "nationwide"

    def test_onsite_default(self) -> None:
        assert detect_location_type("Manchester") == "onsite"


class TestPostcodeExtraction:
    """Extract UK postcodes from text."""

    def test_full_postcode(self) -> None:
        assert extract_postcode("Office at SW1A 1AA, London") == "SW1A 1AA"

    def test_no_space_postcode(self) -> None:
        assert extract_postcode("EC2A1NT") == "EC2A1NT"

    def test_no_postcode(self) -> None:
        assert extract_postcode("Manchester city centre") is None


class TestNormalizeLocationCases:
    """All 10 location cases from SPEC.md §3.4 (Gate P5)."""

    @pytest.mark.asyncio
    async def test_london_default(self) -> None:
        """'London' → Central London coords."""
        result = await normalize_location("London")
        assert result.city == "London"
        assert result.region == "Greater London"
        assert result.latitude == pytest.approx(51.5074, abs=0.01)
        assert result.longitude == pytest.approx(-0.1278, abs=0.01)

    @pytest.mark.asyncio
    async def test_central_london(self) -> None:
        """'Central London' → Central London coords."""
        result = await normalize_location("Central London")
        assert result.latitude == pytest.approx(51.5074, abs=0.01)
        assert result.city == "London"

    @pytest.mark.asyncio
    async def test_city_of_london(self) -> None:
        """'City of London' → EC postcode area."""
        result = await normalize_location("City of London")
        assert result.latitude == pytest.approx(51.5155, abs=0.01)

    @pytest.mark.asyncio
    async def test_remote(self) -> None:
        """'Remote' → location_type=remote, no geometry."""
        result = await normalize_location("Remote")
        assert result.location_type == "remote"
        assert result.latitude is None
        assert result.longitude is None

    @pytest.mark.asyncio
    async def test_hybrid_leeds(self) -> None:
        """'Hybrid - Leeds' → location_type=hybrid, geocode Leeds."""
        uk_cities = {"leeds": (53.8008, -1.5491, "Yorkshire and The Humber")}
        result = await normalize_location("Hybrid - Leeds", uk_cities=uk_cities)
        assert result.location_type == "hybrid"
        assert result.latitude == pytest.approx(53.8008, abs=0.01)

    @pytest.mark.asyncio
    async def test_various_locations(self) -> None:
        """'Various locations' → location_type=nationwide, no geometry."""
        result = await normalize_location("Various locations")
        assert result.location_type == "nationwide"
        assert result.latitude is None

    @pytest.mark.asyncio
    async def test_near_birmingham(self) -> None:
        """'Near Birmingham' → strip 'near', geocode Birmingham."""
        uk_cities = {"birmingham": (52.4862, -1.8904, "West Midlands")}
        result = await normalize_location("Near Birmingham", uk_cities=uk_cities)
        assert result.latitude == pytest.approx(52.4862, abs=0.01)

    @pytest.mark.asyncio
    async def test_south_east_region(self) -> None:
        """'South East' → region only, no city, no geometry."""
        result = await normalize_location("South East")
        assert result.region == "South East"
        assert result.latitude is None

    @pytest.mark.asyncio
    async def test_manchester_city_table(self) -> None:
        """'Manchester' → fallback to city table (Gate P8)."""
        uk_cities = {"manchester": (53.4808, -2.2426, "North West")}
        result = await normalize_location("Manchester", uk_cities=uk_cities)
        assert result.latitude == pytest.approx(53.4808, abs=0.01)
        assert result.longitude == pytest.approx(-2.2426, abs=0.01)

    @pytest.mark.asyncio
    async def test_adzuna_direct_coords(self) -> None:
        """Adzuna job with lat/lon → use directly (Gate P6)."""
        result = await normalize_location(
            "London, UK",
            latitude=51.5074,
            longitude=-0.1278,
            source_name="adzuna",
        )
        assert result.latitude == 51.5074
        assert result.longitude == -0.1278


class TestLocationEdgeCases:
    """Sad paths: null, empty, unknown."""

    @pytest.mark.asyncio
    async def test_empty_location(self) -> None:
        result = await normalize_location("")
        assert result.latitude is None
        assert result.longitude is None

    @pytest.mark.asyncio
    async def test_unknown_location(self) -> None:
        result = await normalize_location("Somewhere in the sky")
        assert result.city == "Somewhere in the sky"
        assert result.latitude is None

    @pytest.mark.asyncio
    async def test_whitespace_only(self) -> None:
        result = await normalize_location("   ")
        assert result.latitude is None


# ── Helper function tests ──


class TestCleanLocationText:
    """Test _clean_location_text helper."""

    def test_strip_hybrid_prefix(self) -> None:
        assert _clean_location_text("Hybrid - Leeds") == "Leeds"

    def test_strip_remote_prefix(self) -> None:
        assert _clean_location_text("Remote - Edinburgh") == "Edinburgh"

    def test_strip_near(self) -> None:
        assert _clean_location_text("near Birmingham") == "Birmingham"

    def test_plain_text(self) -> None:
        assert _clean_location_text("Manchester") == "Manchester"


class TestLocationResult:
    """Test LocationResult defaults."""

    def test_defaults(self) -> None:
        r = LocationResult()
        assert r.city is None
        assert r.region is None
        assert r.postcode is None
        assert r.latitude is None
        assert r.longitude is None
        assert r.location_type == "onsite"


# ── Postcodes.io mock tests (P7) ──


def _mock_client(status_code: int, json_data: object) -> httpx.AsyncClient:
    """Create a mock AsyncClient returning a fixed response."""
    mock = AsyncMock(spec=httpx.AsyncClient)
    resp = httpx.Response(status_code, json=json_data)
    mock.post = AsyncMock(return_value=resp)
    mock.get = AsyncMock(return_value=resp)
    mock.aclose = AsyncMock()
    return mock


class TestGeocodePostcode:
    """Test geocode_postcode with mocked postcodes.io."""

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        client = _mock_client(200, {
            "result": [{"result": {"latitude": 51.5014, "longitude": -0.1419}}],
        })
        coords = await geocode_postcode("SW1A 1AA", client=client)
        assert coords is not None
        assert coords[0] == pytest.approx(51.5014, abs=0.001)
        assert coords[1] == pytest.approx(-0.1419, abs=0.001)

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        client = _mock_client(200, {"result": [{"result": None}]})
        coords = await geocode_postcode("ZZ99 9ZZ", client=client)
        assert coords is None

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        client = _mock_client(200, {"result": []})
        coords = await geocode_postcode("ZZ99 9ZZ", client=client)
        assert coords is None

    @pytest.mark.asyncio
    async def test_http_error(self) -> None:
        mock = AsyncMock(spec=httpx.AsyncClient)
        mock.post = AsyncMock(side_effect=httpx.ConnectError("fail"))
        mock.aclose = AsyncMock()
        coords = await geocode_postcode("SW1A 1AA", client=mock)
        assert coords is None

    @pytest.mark.asyncio
    async def test_server_error(self) -> None:
        client = _mock_client(500, {"error": "server error"})
        coords = await geocode_postcode("SW1A 1AA", client=client)
        assert coords is None

    @pytest.mark.asyncio
    async def test_no_client_provided(self) -> None:
        """When no client is provided, function creates its own (should not crash)."""
        # This will fail to connect but should handle gracefully
        coords = await geocode_postcode("ZZ99 9ZZ")
        assert coords is None


class TestGeocodePlace:
    """Test geocode_place with mocked postcodes.io."""

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        client = _mock_client(200, {
            "result": [{"latitude": 53.4808, "longitude": -2.2426, "region": "North West"}],
        })
        result = await geocode_place("Manchester", client=client)
        assert result is not None
        assert result[0] == pytest.approx(53.4808, abs=0.001)
        assert result[1] == pytest.approx(-2.2426, abs=0.001)
        assert result[2] == "North West"

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        client = _mock_client(200, {"result": []})
        result = await geocode_place("Nowhereville", client=client)
        assert result is None

    @pytest.mark.asyncio
    async def test_null_result(self) -> None:
        client = _mock_client(200, {"result": None})
        result = await geocode_place("Nowhereville", client=client)
        assert result is None

    @pytest.mark.asyncio
    async def test_http_error(self) -> None:
        mock = AsyncMock(spec=httpx.AsyncClient)
        mock.get = AsyncMock(side_effect=httpx.ConnectError("fail"))
        mock.aclose = AsyncMock()
        result = await geocode_place("Manchester", client=mock)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_client_provided(self) -> None:
        result = await geocode_place("ZZNowhere")
        assert result is None


# ── normalize_location with mocked HTTP (postcodes.io paths) ──


class TestNormalizeLocationWithHttp:
    """Cover postcodes.io code paths in normalize_location."""

    @pytest.mark.asyncio
    async def test_postcode_geocoding(self) -> None:
        """Postcode in text → geocode via postcodes.io."""
        client = _mock_client(200, {
            "result": [{"result": {"latitude": 51.5014, "longitude": -0.1419}}],
        })
        result = await normalize_location("Office SW1A 1AA", http_client=client)
        assert result.postcode == "SW1A 1AA"
        assert result.latitude == pytest.approx(51.5014, abs=0.001)

    @pytest.mark.asyncio
    async def test_postcode_geocoding_fails(self) -> None:
        """Postcode found but geocoding fails → fall through to other methods."""
        client = _mock_client(200, {"result": [{"result": None}]})
        result = await normalize_location("Office SW1A 1AA", http_client=client)
        assert result.postcode == "SW1A 1AA"
        # Falls through, no city match, so city is extracted from text
        assert result.city == "Office SW1A 1AA"

    @pytest.mark.asyncio
    async def test_london_outcode(self) -> None:
        """'London EC2' → outcode lookup via postcodes.io."""
        client = _mock_client(200, {
            "result": {"latitude": 51.515, "longitude": -0.082},
        })
        result = await normalize_location("London EC2", http_client=client)
        assert result.city == "London"
        assert result.region == "Greater London"
        assert result.latitude == pytest.approx(51.515, abs=0.01)

    @pytest.mark.asyncio
    async def test_london_outcode_fails(self) -> None:
        """'London EC2' with outcode lookup failure → default London coords."""
        client = _mock_client(404, {})
        result = await normalize_location("London EC2", http_client=client)
        assert result.city == "London"
        assert result.latitude == pytest.approx(51.5074, abs=0.01)

    @pytest.mark.asyncio
    async def test_london_outcode_http_error(self) -> None:
        """'London EC2' with HTTP error → default London coords."""
        mock = AsyncMock(spec=httpx.AsyncClient)
        mock.get = AsyncMock(side_effect=httpx.ConnectError("fail"))
        mock.aclose = AsyncMock()
        result = await normalize_location("London EC2", http_client=mock)
        assert result.city == "London"
        assert result.latitude == pytest.approx(51.5074, abs=0.01)

    @pytest.mark.asyncio
    async def test_city_via_places_api(self) -> None:
        """Unknown city → try postcodes.io places API."""
        client = _mock_client(200, {
            "result": [{"latitude": 50.3755, "longitude": -4.1427, "region": "South West"}],
        })
        # Use get for places endpoint
        result = await normalize_location("Plymouth", http_client=client)
        assert result.latitude == pytest.approx(50.3755, abs=0.01)
        assert result.region == "South West"
        assert result.city == "Plymouth"

    @pytest.mark.asyncio
    async def test_city_places_api_fails_then_fallback(self) -> None:
        """Places API returns nothing → fall back to city table."""
        client = _mock_client(200, {"result": []})
        uk_cities = {"plymouth": (50.3755, -4.1427, "South West")}
        result = await normalize_location("Plymouth", http_client=client, uk_cities=uk_cities)
        assert result.latitude == pytest.approx(50.3755, abs=0.01)

    @pytest.mark.asyncio
    async def test_london_with_area(self) -> None:
        """'East London' → London areas lookup."""
        result = await normalize_location("East London")
        assert result.latitude == pytest.approx(51.5311, abs=0.01)
        assert result.city == "London"

    @pytest.mark.asyncio
    async def test_london_south(self) -> None:
        """'South London' → London areas lookup."""
        result = await normalize_location("South London")
        assert result.latitude == pytest.approx(51.4620, abs=0.01)

    @pytest.mark.asyncio
    async def test_multiple_regions(self) -> None:
        """Test various UK region strings."""
        for region in ["North West", "East Midlands", "Scotland", "Wales", "Northern Ireland"]:
            result = await normalize_location(region)
            assert result.region == region
            assert result.latitude is None
