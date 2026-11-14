# CitizenTech · Componente Dados — Pipeline do Assistente de Mobilidade por Ônibus

**Global Solution 2026.2 · Engenharia de Software 4º ano · Big Data Architecture & Data Integration**

## 👥 Equipe

| Integrante | RM |
|---|---|
| Guilherme Santiago da Silva | RM552321 |
| Gustavo Govea Soares | RM553842 |
| Pedro Henrique Mello Silva Alves | RM554223 |
| Gabriel Borba | RM553187 |

---

## 🎯 Objetivo

Este repositório materializa o componente **"Dados"** do MVP da CitizenTech. O pipeline demonstra um fluxo funcional de dados do bruto ao curado, orquestrado por Apache Airflow, que alimenta os modelos de IA e a interface do assistente de mobilidade para pessoas cegas ou com baixa visão.

**Entregáveis principais:**
- ✅ **Pipeline funcional** — DAGs Airflow executando ETL/ELT de ponta a ponta
- ✅ **Arquitetura em camadas** — Raw → Staging (Parquet) → Curada (MySQL 8.4)
- ✅ **Dicionário de dados** — Todas as tabelas com tipos, chaves e exemplos
- ✅ **PDF de entrega** — Diagrama de arquitetura + dicionário de dados em um único arquivo
- ✅ **Prints do Airflow** — Evidências de execução abaixo

---

## 📂 O que contém este Repositório

```
dags/                       DAGs do Airflow (só orquestram; a lógica fica em pipeline/)
pipeline/
  extract.py               ingestão raw + sha256
  transform.py             GTFS → linha, letreiro, parada, itinerario, frequencia (Parquet)
  quality.py               portão de qualidade (18 checagens)
  load.py                  carga transacional + linhagem
  matching.py              contrato com a visão computacional (OCR → letreiro)
  metrics.py               DAG 2: indicadores de impacto
  simulacao.py             eventos simulados com premissas documentadas
  run_local.py             executor sem Airflow
sql/schema_mysql.sql        DDL gerado do schema
docs/                       arquitetura, dicionário, evidências, PDF de entrega
tests/                      testes com mini-GTFS sintético
```

---

## 🖼️ Printfs do Airflow — Evidências de Execução

As prints abaixo comprovam o pipeline rodando de forma orquestrada. Cada uma está linkada para visualização direta no repositório.

### DAG 1 — `citizentech_gtfs_sptrans` (GTFS SPTrans → MySQL)

| Print | Link | Justificativa |
|---|---|---|
| **00_airflow_login.png** | `docs/evidencias/prints_airflow/00_airflow_login.png` | Comprova o acesso à interface do Airflow (localhost:8080). O login admin confirma que o ambiente está configurado e pronto para receber os DAGs. |
| **01_airflow_home_dags.png** | `docs/evidencias/prints_airflow/01_airflow_home_dags.png` | Visão geral dos dois DAGs ativos (citizentech_gtfs_sptrans e citizentech_indicadores_reconhecimento). Confirma que ambos estão carregados no Airflow 2.10.5. |
| **02_dag_gtfs_grid.png** | `docs/evidencias/prints_airflow/02_dag_gtfs_grid.png` | Grid da DAG 1 mostrando tasks em execução bem-sucedida. Valida o pipeline funcional: extrair → versão nova? → transformar → checar qualidade → carregar → publicar pacote offline. |
| **03_dag_gtfs_graph.png** | `docs/evidencias/prints_airflow/03_dag_gtfs_graph.png` | Visualização gráfica do fluxo da DAG 1. Demonstra a arquitetura orquestrada de ETL/ELT com todas as dependências entre tasks. |

### DAG 2 — `citizentech_indicadores_reconhecimento` (Eventos → Indicadores)

| Print | Link | Justificativa |
|---|---|---|
| **04_dag_indicadores_grid.png** | `docs/evidencias/prints_airflow/04_dag_indicadores_grid.png` | Grid da DAG 2 mostrando a task de simulação (parâmetro `simular: true`) e o cálculo de indicadores. Valida o pipeline de geração de métricas de reconhecimento de letreiros. |
| **05_dag_indicadores_graph.png** | `docs/evidencias/prints_airflow/05_dag_indicadores_graph.png` | Fluxo gráfico da DAG 2. Demonstra a transformação de eventos brutos em dados analíticos (taxa de acerto p50/p95, latência, acerto à noite). |
| **06_dagruns_gtfs.png** | `docs/evidencias/prints_airflow/06_dagruns_gtfs.png` | Histórico de execuções (dagrun) da DAG 1. Comprova a idempotência do pipeline: primeira execução com status "sucesso" e reexecução com mesmo SHA-256 tem status "ignorada" (não duplica dados). |
| **07_dagruns_indicadores.png** | `docs/evidencias/prints_airflow/07_dagruns_indicadores.png` | Histórico de execuções da DAG 2. Demonstra que o pipeline funciona de forma repetível e diária, conforme o schedule configurado. |

---

## 🏗️ Arquitetura em Camadas

![Arquitetura do pipeline](docs/arquitetura.svg)

- **Raw (imutável):** o zip original, identificado pelo SHA-256. Permite reprocessar sem baixar de novo.
- **Staging (Parquet):** tabelas tipadas e normalizadas por execução.
- **Curada (MySQL 8.4):** carga em **uma transação** com reconciliação staging × banco. Reexecutar com o mesmo feed **não duplica nada** (o DAG pula por short-circuit).
- **Entrega:** banco para a API + pacote offline para o app.

**18 checagens de qualidade** atuam como portão: se uma crítica falha, nada é carregado e o MVP segue com a última versão boa.

---

## 📚 Dicionário de Dados

Dicionário completo disponível em: [docs/dicionario_de_dados.md](docs/dicionario_de_dados.md)

Tabelas principais:
- `linha` — 1.365 linhas de ônibus (route_id, número, nome, cor)
- `letreiro` — 2.268 letreiros (vocabulário do OCR)
- `parada` — 22.270 paradas com coordenadas (lat, lon)
- `itinerario` — 99.071 sequências de paradas por letreiro
- `frequencia` — 40.337 faixas horárias com intervalos
- `evento_reconhecimento` — 500 eventos de reconhecimento do app
- `indicador_reconhecimento_diario` — Indicadores diários de impacto
- `carga_controle` — Linhagem: versão do feed, status e contagens por carga

**DDL do MySQL:** [sql/schema_mysql.sql](sql/schema_mysql.sql)

---

## ▶️ Como Executar o Pipeline

### Opção A — Airflow com Docker (recomendado)

```bash
cp .env.example .env          # troque as senhas
docker compose up -d --build  # sobe MySQL, Postgres, Airflow webserver e scheduler
```

1. Acesse http://localhost:8080 com `admin` / `admin_local`
2. Dispare `citizentech_gtfs_sptrans` (▶ Trigger DAG)
3. Dispare `citizentech_indicadores_reconhecimento` com `{"simular": true}`
4. Dados disponíveis no MySQL (porta 3306 em 127.0.0.1)

### Opção B — Sem Docker (banco SQLite local)

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m pipeline.run_local tudo      # GTFS + simulação + indicadores
.venv\Scripts\python -m pipeline.run_local gtfs      # reexecução: status "ignorada" (idempotente)
.venv\Scripts\python -m pytest -q                    # 10 testes
.venv\Scripts\python -m scripts.gerar_documentação   # dicionário + consultas
```

### Opção C — GitHub Actions

O workflow `.github/workflows/pipeline.yml` roda a cada push: testes, carga dos DAGs no Airflow 2.10.5, `airflow dags test`, reexecução para provar idempotência e conferência de contagens. Logs e `letreiros.json` ficam como artefato `evidencias-pipeline`.

---

## 📦 Dados: Origem, Licença e Decisões

- **GTFS SPTrans** — via espelho público do [Mobility Database](https://mobilitydatabase.org) (`mdb-8`), sem cadastro necessário. Versão carregada: sha256 `457293b83e34…` (atualizado em 10/11/2026).
- **Eventos simulados** — Enquanto não há testes de campo, o DAG 2 gera eventos marcados `origem = 'simulado'` com premissas documentadas em `pipeline/simulacao.py`. **Não são resultados medidos do produto.**
- **Tempo real (Olho Vivo)** — Não está no MVP; exige token e não é necessário para o fluxo central.
- **shapes.txt (60 MB)** — Fica apenas no Raw; o app não desenha o traçado, só precisa da sequência de paradas.

---

## 🔗 Link do Repositório

GitHub: [https://github.com/seu-organization/citizentech-dados](https://github.com/seu-organization/citizentech-dados)

*(Substitua pelo link real antes do envio)*