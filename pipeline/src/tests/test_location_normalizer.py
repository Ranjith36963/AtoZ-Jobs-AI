"""Tests for location normalizer (SPEC.md §3.4, Gates P5–P8)."""

import pytest

from src.processing.location import (
    detect_location_type,
    extract_postcode,
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
