import pytest
import respx
from httpx import Response, TimeoutException

from src.ebird.ebird import EBird, RegionType
from src.utils.api_exceptions import (
    ApiError,
    AuthenticationError,
    NetworkError,
    ServerError,
)

EBIRD_API_URL = "https://api.ebird.org/v2/ref/region/list/subnational1/CN"


@pytest.fixture
def ebird_client():
    # We use a dummy token because we are mocking the API responses
    return EBird(token="dummy_token")


@pytest.mark.asyncio
@respx.mock
async def test_call_success(ebird_client):
    # Mock the API response for a successful call
    respx.get(EBIRD_API_URL).mock(
        return_value=Response(200, json=[{"name": "Beijing"}])
    )

    regions = await ebird_client.get_regions(RegionType.SUBNATIONAL1, "CN")
    assert regions[0]["name"] == "Beijing"


@pytest.mark.asyncio
@respx.mock
async def test_call_authentication_error(ebird_client):
    # Mock a 401 Unauthorized response
    respx.get(EBIRD_API_URL).mock(return_value=Response(401))

    with pytest.raises(AuthenticationError):
        await ebird_client.get_regions(RegionType.SUBNATIONAL1, "CN")


@pytest.mark.asyncio
@respx.mock
async def test_call_server_error_retry(ebird_client):
    # Mock a 500 Internal Server Error response, which should trigger retries
    mock_route = respx.get(EBIRD_API_URL).mock(
        side_effect=[
            Response(500),
            Response(500),
            Response(200, json=[{"name": "Beijing_after_retry"}]),
        ]
    )

    regions = await ebird_client.get_regions(RegionType.SUBNATIONAL1, "CN")
    assert regions[0]["name"] == "Beijing_after_retry"
    assert mock_route.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_call_server_error_fail_after_retries(ebird_client):
    # Mock a persistent 500 error
    respx.get(EBIRD_API_URL).mock(return_value=Response(500))

    with pytest.raises(ServerError):
        await ebird_client.get_regions(RegionType.SUBNATIONAL1, "CN")


@pytest.mark.asyncio
@respx.mock
async def test_call_network_error_retry(ebird_client):
    # Mock a network timeout
    mock_route = respx.get(EBIRD_API_URL).mock(
        side_effect=[
            TimeoutException("Connection timed out"),
            TimeoutException("Connection timed out"),
            Response(200, json=[{"name": "Beijing_after_timeout"}]),
        ]
    )

    regions = await ebird_client.get_regions(RegionType.SUBNATIONAL1, "CN")
    assert regions[0]["name"] == "Beijing_after_timeout"
    assert mock_route.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_call_api_error_on_bad_json(ebird_client):
    # Mock a response with invalid JSON
    respx.get(EBIRD_API_URL).mock(return_value=Response(200, text="not json"))

    with pytest.raises(ApiError):
        await ebird_client.get_regions(RegionType.SUBNATIONAL1, "CN")
