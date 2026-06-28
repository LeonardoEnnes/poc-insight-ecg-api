import pytest
from unittest.mock import patch, AsyncMock
from app.infrastructure.if_cloud_client import IFCloudClient, IFCloudIntegrationError
from app.core.exceptions import IFCloudIntegrationException
import httpx

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_if_client_raises_401_on_invalid_token(mock_get):
    mock_response = AsyncMock()
    mock_response.status_code = 401
    mock_get.return_value = mock_response

    client = IFCloudClient()

    with pytest.raises(IFCloudIntegrationException):
        await client.get_observation("123", "token_invalido", 0)

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_if_client_raises_502_on_network_timeout(mock_get):
    mock_get.side_effect = httpx.RequestError("Timeout")

    client = IFCloudClient()

    with pytest.raises(IFCloudIntegrationException):
        await client.get_observation("123", "token_valido", 0)