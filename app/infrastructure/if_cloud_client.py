import httpx
from typing import Dict, Any

class IFCloudIntegrationError(Exception):
    """Exceção customizada para erros de comunicação com o IF-Cloud."""
    pass

class IFCloudClient:
    def __init__(self, base_url: str = "https://if4health.charqueadas.ifsul.edu.br/biofass"):
        self.base_url = base_url.rstrip("/")

    async def get_observation(self, observation_id: str, access_token: str, minute: int ) -> Dict[str, Any]:
        """
        Busca o Observation no servidor FHIR do IF-Cloud.
        """
        url = f"{self.base_url}/Observation/{observation_id}/data/{minute}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }

        # verify=False contorna problemas de certificado SSL no ambiente do IF
        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            try:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 401:
                    raise IFCloudIntegrationError("Falha de Autenticação: Token inválido ou expirado.")
                    
                if response.status_code == 404:
                    raise IFCloudIntegrationError(f"Observation ID '{observation_id}' não encontrado no IF-Cloud.")

                response.raise_for_status()
                return response.json()
                
            except httpx.RequestError as exc:
                raise IFCloudIntegrationError(f"Erro de conexão ao acessar o IF-Cloud: {exc}")