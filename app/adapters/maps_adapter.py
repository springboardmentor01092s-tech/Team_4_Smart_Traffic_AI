"""
app/adapters/maps_adapter.py

Maps/Routing adapter for TrafficVision AI Milestone 2.

Provides:
  MapsAdapterProtocol  — abstract interface any provider must satisfy.
  OSRMAdapter          — concrete implementation using the OSRM HTTP API.
  RouteInfo            — typed result dataclass.

Architecture:
  RouteService
      |
      v
  MapsAdapterProtocol
      |
      v
  OSRMAdapter  -->  OSRM HTTP API (e.g. router.project-osrm.org)

Design decisions:
  - Fully async using httpx.AsyncClient.
  - OSRMAdapter isolates all provider-specific HTTP and JSON parsing.
  - All provider exceptions are caught and re-raised as MapsProviderError,
    preventing raw httpx / network errors from leaking to the service layer.
  - Configuration is loaded from app.core.config (maps_provider_url, maps_api_key).
  - OSRM basic usage requires no API key.
  - HTTP calls in tests MUST be mocked — no live OSRM calls in the test suite.

OSRM Route API:
  GET {base_url}/route/v1/driving/{lng1},{lat1};{lng2},{lat2}
  Response includes routes[].duration (seconds), routes[].distance (meters).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.exceptions import MapsProviderError

logger = logging.getLogger(__name__)

# Default OSRM public demo server. Override via MAPS_PROVIDER_URL env var.
_DEFAULT_OSRM_BASE_URL = "http://router.project-osrm.org"
_REQUEST_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class RouteInfo:
    """
    Result of a routing lookup between two geographic points.

    Attributes:
        distance_meters:   Total route distance in metres.
        duration_seconds:  Estimated travel duration in seconds (free-flow).
        distance_km:       Convenience property: distance in kilometres.
        duration_minutes:  Convenience property: duration in minutes.
    """

    distance_meters: float
    duration_seconds: float

    @property
    def distance_km(self) -> float:
        return self.distance_meters / 1000.0

    @property
    def duration_minutes(self) -> float:
        return self.duration_seconds / 60.0


class MapsAdapterProtocol(Protocol):
    """
    Abstract interface for a Maps/Routing provider.

    Any class implementing this protocol can be injected into RouteService.
    """

    async def get_route(
        self,
        *,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> RouteInfo:
        """
        Fetch routing information between two geographic coordinates.

        Args:
            origin_lat: Latitude of the origin point.
            origin_lng: Longitude of the origin point.
            dest_lat:   Latitude of the destination point.
            dest_lng:   Longitude of the destination point.

        Returns:
            RouteInfo with distance and duration.

        Raises:
            MapsProviderError: On any provider failure.
        """
        ...


class OSRMAdapter:
    """
    Concrete OSRM routing adapter.

    Uses the OSRM Route service API (v1):
      GET {base_url}/route/v1/driving/{lng1},{lat1};{lng2},{lat2}
        ?overview=false&steps=false

    The adapter:
      - Issues async HTTP GET requests.
      - Validates the response structure.
      - Re-raises any error as MapsProviderError.
      - Logs warnings for non-200 responses and timeouts.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_OSRM_BASE_URL,
        api_key: str | None = None,
        timeout: float = _REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key  # OSRM public server does not require a key
        self._timeout = timeout

    async def get_route(
        self,
        *,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> RouteInfo:
        """
        Fetch routing info between two points using OSRM.

        Raises:
            MapsProviderError: On HTTP error, timeout, connection failure,
                               or malformed response.
        """
        coords = f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
        url = f"{self._base_url}/route/v1/driving/{coords}"
        params: dict[str, str] = {"overview": "false", "steps": "false"}
        if self._api_key:
            params["key"] = self._api_key

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
        except httpx.TimeoutException as exc:
            logger.warning("OSRM request timed out | url=%s | error=%s", url, exc)
            raise MapsProviderError(
                f"Request to OSRM timed out after {self._timeout}s."
            ) from exc
        except httpx.ConnectError as exc:
            logger.warning("OSRM connection failed | url=%s | error=%s", url, exc)
            raise MapsProviderError(
                f"Cannot connect to OSRM at {self._base_url}."
            ) from exc
        except httpx.RequestError as exc:
            logger.warning("OSRM request error | url=%s | error=%s", url, exc)
            raise MapsProviderError(f"OSRM request failed: {exc}") from exc

        if response.status_code != 200:
            logger.warning(
                "OSRM returned HTTP %d | url=%s | body=%s",
                response.status_code,
                url,
                response.text[:200],
            )
            raise MapsProviderError(
                f"OSRM returned HTTP {response.status_code}."
            )

        try:
            data = response.json()
        except Exception as exc:
            raise MapsProviderError("OSRM returned malformed JSON.") from exc

        if data.get("code") != "Ok":
            raise MapsProviderError(
                f"OSRM error code: {data.get('code', 'unknown')} — "
                f"{data.get('message', 'no message')}."
            )

        try:
            route = data["routes"][0]
            distance_m = float(route["distance"])
            duration_s = float(route["duration"])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise MapsProviderError(
                f"Unexpected OSRM response structure: {exc}"
            ) from exc

        logger.debug(
            "OSRM route | %.4f,%.4f -> %.4f,%.4f | dist=%.0fm dur=%.0fs",
            origin_lat, origin_lng, dest_lat, dest_lng,
            distance_m, duration_s,
        )
        return RouteInfo(distance_meters=distance_m, duration_seconds=duration_s)
