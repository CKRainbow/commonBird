import pytest
import respx
from httpx import Response, TimeoutException

from src.birdreport.birdreport import Birdreport
from src.utils.api_exceptions import (
    ApiError,
    AuthenticationError,
    NetworkError,
    ServerError,
)

BIRDREPORT_API_URL = "https://api.birdreport.cn/member/system/user/get"


@pytest.fixture
def birdreport_client():
    # We use a dummy token because we are mocking the API responses
    return Birdreport(token="dummy_token")


@pytest.mark.asyncio
@respx.mock
async def test_get_data_success(birdreport_client):
    # Mock the API response for a successful call
    respx.post(BIRDREPORT_API_URL).mock(
        return_value=Response(200, json={"code": 200, "data": {"username": "testuser"}})
    )

    user_info = await birdreport_client.member_get_user()
    assert user_info["username"] == "testuser"


@pytest.mark.asyncio
@respx.mock
async def test_get_data_authentication_error(birdreport_client):
    # Mock a 401 Unauthorized response
    respx.post(BIRDREPORT_API_URL).mock(return_value=Response(401))

    with pytest.raises(AuthenticationError):
        await birdreport_client.member_get_user()


@pytest.mark.asyncio
@respx.mock
async def test_get_data_server_error_retry(birdreport_client):
    # Mock a 500 Internal Server Error response, which should trigger retries
    mock_route = respx.post(BIRDREPORT_API_URL).mock(
        side_effect=[
            Response(500),
            Response(500),
            Response(
                200, json={"code": 200, "data": {"username": "testuser_after_retry"}}
            ),
        ]
    )

    user_info = await birdreport_client.member_get_user()
    assert user_info["username"] == "testuser_after_retry"
    assert mock_route.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_get_data_server_error_fail_after_retries(birdreport_client):
    # Mock a persistent 500 error
    respx.post(BIRDREPORT_API_URL).mock(return_value=Response(500))

    with pytest.raises(ServerError):
        await birdreport_client.member_get_user()


@pytest.mark.asyncio
@respx.mock
async def test_get_data_network_error_retry(birdreport_client):
    # Mock a network timeout
    mock_route = respx.post(BIRDREPORT_API_URL).mock(
        side_effect=[
            TimeoutException("Connection timed out"),
            TimeoutException("Connection timed out"),
            Response(
                200, json={"code": 200, "data": {"username": "testuser_after_timeout"}}
            ),
        ]
    )

    user_info = await birdreport_client.member_get_user()
    assert user_info["username"] == "testuser_after_timeout"
    assert mock_route.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_get_data_api_error_on_bad_json(birdreport_client):
    # Mock a response with invalid JSON
    respx.post(BIRDREPORT_API_URL).mock(return_value=Response(200, text="not json"))

    with pytest.raises(ApiError):
        await birdreport_client.member_get_user()
