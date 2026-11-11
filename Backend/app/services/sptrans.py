import httpx


class SPTransService:
    def __init__(self, client: httpx.AsyncClient, base_url: str, token: str) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.authenticated = False

    async def authenticate(self) -> bool:
        """Autentica na SPTrans; o AsyncClient mantém cookies da sessão."""
        response = await self.client.post(
            f"{self.base_url}/Login/Autenticar",
            params={"token": self.token},
        )
        response.raise_for_status()

        result = response.text.strip().lower().strip('"')
        self.authenticated = result == "true"
        return self.authenticated
