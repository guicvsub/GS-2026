# SemáforoFácil — esqueleto do MVP

Site em que a pessoa fotografa a botoeira de um semáforo, a visão mede o estado,
a IA escreve o relato, o robô registra no 156 e o painel mostra os pontos críticos.

## Rodar tudo
```bash
cp .env.example .env          # ajuste a senha
docker compose up --build     # app + banco  -> http://localhost:8000/docs
docker compose --profile dados up       # + Airflow -> http://localhost:8080
docker compose --profile monitoramento up   # + Prometheus (9090) e Grafana (3000)
```

## Onde cada disciplina entra
| Disciplina | Onde mexer |
|---|---|
| Dados | `db/init.sql` (contrato de dados), `pipeline/dags/` |
| DevOps | `app/Dockerfile`, `docker-compose.yml`, `.github/workflows/`, `infra/`, `monitoring/` |
| Visão | novo `app/visao.py`; grava contraste, tamanho_relativo, classificacao em `relatos` |
| IA Generativa | novo `app/ia.py`; grava descricao e texto_relato |
| RPA | robô UiPath lê `GET /relatos?status=confirmado` e grava protocolo_156 |
| BI/Startup | Lean Canvas e pitch em `docs/` |
| Maker | arquivos CAD/DXF/STL em `docs/maker/` |

## Ficha Técnica do MVP
Preencher: nome, cidadão e território, problema (1 frase), proposta de valor, arquitetura,
fontes de dados, modelos de IA, URL do MVP, repositório, indicadores e ODS (10 e 11).

Os semáforos em `db/init.sql` são DADOS SIMULADOS; documentar isso no dicionário de dados.
