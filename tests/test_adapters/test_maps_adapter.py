"""
tests/test_adapters/test_maps_adapter.py

Unit tests for OSRMAdapter using mocked httpx responses.
No live OSRM calls are made.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from app.adapters.maps_adapter import OSRMAdapter, RouteInfo
from app.core.exceptions import MapsProviderError


def _make_response(
    status_code: int = 200,
    json_data: dict | None = None,
    text: str = "",
) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


_OSRM_SUCCESS_RESPONSE = {
    "code": "Ok",
    "routes": [
        {
            "distance": 12500.0,   # meters
            "duration": 750.0,     # seconds = 12.5 min
        }
    ],
}


class TestOSRMAdapter:
    @pytest.fixture
    def adapter(self) -> OSRMAdapter:
        return OSRMAdapter(base_url="http://mock-osrm.local", timeout=5.0)

    async def test_get_route_success(self, adapter: OSRMAdapter) -> None:
        mock_resp = _make_response(200, _OSRM_SUCCESS_RESPONSE)
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        with patch("app.adapters.maps_adapter.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value = mock_client
            result = await adapter.get_route(
                origin_lat=51.5, origin_lng=-0.1,
                dest_lat=51.6, dest_lng=-0.2,
            )

        assert isinstance(result, RouteInfo)
        assert result.distance_meters == pytest.approx(12500.0)
        assert result.duration_seconds == pytest.approx(750.0)
        assert result.distance_km == pytest.approx(12.5)
        assert result.duration_minutes == pytest.approx(12.5)

    async def test_get_route_non_200_raises(self, adapter: OSRMAdapter) -> None:
        mock_resp = _make_response(503, text="Service Unavailable")
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        with patch("app.adapters.maps_adapter.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value = mock_client
            with pytest.raises(MapsProviderError, match="HTTP 503"):
                await adapter.get_route(
                    origin_lat=51.5, origin_lng=-0.1,
                    dest_lat=51.6, dest_lng=-0.2,
                )

    async def test_get_route_osrm_error_code_raises(self, adapter: OSRMAdapter) -> None:
        mock_resp = _make_response(200, {"code": "InvalidUrl", "message": "Bad coords"})
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        with patch("app.adapters.maps_adapter.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value = mock_client
            with pytest.raises(MapsProviderError, match="InvalidUrl"):
                await adapter.get_route(
                    origin_lat=0.0, origin_lng=0.0,
                    dest_lat=0.0, dest_lng=0.0,
                )

    async def test_get_route_timeout_raises(self, adapter: OSRMAdapter) -> None:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timeout", request=MagicMock())

        with patch("app.adapters.maps_adapter.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value = mock_client
            with pytest.raises(MapsProviderError, match="timed out"):
                await adapter.get_route(
                    origin_lat=51.5, origin_lng=-0.1,
                    dest_lat=51.6, dest_lng=-0.2,
                )

    async def test_get_route_connection_error_raises(self, adapter: OSRMAdapter) -> None:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("cannot connect")

        with patch("app.adapters.maps_adapter.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value = mock_client
            with pytest.raises(MapsProviderError, match="Cannot connect"):
                await adapter.get_route(
                    origin_lat=1.0, origin_lng=1.0,
                    dest_lat=2.0, dest_lng=2.0,
                )

    async def test_get_route_malformed_json_raises(self, adapter: OSRMAdapter) -> None:
        mock_resp = _make_response(200, text="not-json")
        mock_resp.json.side_effect = ValueError("bad json")
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        with patch("app.adapters.maps_adapter.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value = mock_client
            with pytest.raises(MapsProviderError, match="malformed JSON"):
                await adapter.get_route(
                    origin_lat=51.5, origin_lng=-0.1,
                    dest_lat=51.6, dest_lng=-0.2,
                )

    async def test_get_route_missing_routes_key_raises(self, adapter: OSRMAdapter) -> None:
        mock_resp = _make_response(200, {"code": "Ok", "routes": []})
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        with patch("app.adapters.maps_adapter.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value = mock_client
            with pytest.raises(MapsProviderError, match="structure"):
                await adapter.get_route(
                    origin_lat=51.5, origin_lng=-0.1,
                    dest_lat=51.6, dest_lng=-0.2,
                )
