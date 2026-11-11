# SPTrans Olho Vivo API

Template mínimo em FastAPI para verificar a conexão e a autenticação com a API oficial Olho Vivo da SPTrans. Inclui apenas `/health` e `/sptrans/status`.

## Requisitos

Python 3.10 ou superior.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Configuração

Edite o arquivo `.env` e informe o token obtido no portal de desenvolvedores da SPTrans:

```env
SPTRANS_BASE_URL=https://api.olhovivo.sptrans.com.br/v2.1
SPTRANS_TOKEN=seu_token_aqui
```

O arquivo `.env` não deve ser enviado ao Git. O `.gitignore` já o exclui. O projeto inclui `.env.example` sem credenciais reais.

## Execução

Na pasta do projeto, execute:

```bash
uvicorn app.main:app --reload
```

A API ficará disponível em `http://127.0.0.1:8000`.

## Endpoints

- `GET http://127.0.0.1:8000/health` — confirma que a API está ativa.
- `GET http://127.0.0.1:8000/sptrans/status` — informa se o token está configurado e tenta autenticar na SPTrans.
- `GET http://127.0.0.1:8000/docs` — documentação interativa do Swagger.

A autenticação real só será verificada depois de configurar um token válido. O cliente HTTPX da aplicação mantém os cookies de sessão recebidos da SPTrans para futuras rotas.

A chamada de autenticação segue a documentação oficial: `POST /Login/Autenticar?token={token}`. O template não implementa consultas de linhas, paradas ou veículos.

## Referência

[Documentação oficial da API Olho Vivo](https://www.sptrans.com.br/desenvolvedores/api-do-olho-vivo-guia-de-referencia/documentacao-api/)
