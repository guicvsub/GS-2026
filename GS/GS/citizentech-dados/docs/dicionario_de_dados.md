# Dicionário de dados — camada curada (MySQL `citizentech`)

Gerado automaticamente por `python -m scripts.gerar_documentacao` a partir de `pipeline/schema.py` e do banco carregado. Exemplos são valores reais da última carga.

## `linha`

Linhas de ônibus da SPTrans (fonte: GTFS). Camada: curada (DAG 1. fonte GTFS SPTrans). Linhas na última carga: **1.366**.

| Coluna | Tipo (MySQL) | Chave | Nulo | Descrição | Exemplo |
|---|---|---|---|---|---|
| `route_id` | VARCHAR(20) | PK | não | ID GTFS da linha, ex. 8000-10 | 1012-10 |
| `numero` | VARCHAR(10) |  | não | Parte numérica do letreiro, ex. 8000 | 1012 |
| `sufixo` | VARCHAR(5) |  | sim | Sufixo após o hífen, ex. 10 | 10 |
| `nome` | VARCHAR(160) |  | não | Nome longo: terminal A - terminal B | Term. Jd. Britania - Jd. Monte Belo |
| `tipo_transporte` | SMALLINT |  | não | route_type GTFS (3 = ônibus) | 3 |
| `cor_hex` | VARCHAR(6) |  | sim | Cor oficial da linha (RGB hex), usada na interface | 509E2F |
| `execucao_id` | VARCHAR(40) |  | não | Execução do pipeline que gravou a linha (FK lógica p/ carga_controle) | gtfs_20261113T202011192633_ae07f1c3 |

## `letreiro`

Texto do painel do ônibus por sentido; vocabulário do OCR. Camada: curada (DAG 1. fonte GTFS SPTrans). Linhas na última carga: **2.269**.

| Coluna | Tipo (MySQL) | Chave | Nulo | Descrição | Exemplo |
|---|---|---|---|---|---|
| `letreiro_id` | VARCHAR(30) | PK | não | route_id + '_' + sentido | 1012-10_0 |
| `route_id` | VARCHAR(20) | FK → linha.route_id | não | Linha à qual o letreiro pertence | 1012-10 |
| `sentido` | SMALLINT |  | não | direction_id GTFS (0 ida, 1 volta) | 0 |
| `destino` | VARCHAR(120) |  | não | trip_headsign, como aparece no ônibus | Jd. Monte Belo |
| `texto_letreiro` | VARCHAR(160) |  | não | numero-sufixo + destino | 1012-10 Jd. Monte Belo |
| `texto_normalizado` | VARCHAR(160) |  | não | Sem acento, maiúsculo, sem pontuação | 1012 10 JD MONTE BELO |
| `trip_id_referencia` | VARCHAR(40) |  | não | Viagem GTFS usada como modelo do sentido | 1012-10-0 |
| `execucao_id` | VARCHAR(40) |  | não | Execução do pipeline que gravou a linha (FK lógica p/ carga_controle) | gtfs_20261113T202011192633_ae07f1c3 |

## `parada`

Pontos de ônibus com coordenadas. Camada: curada (DAG 1. fonte GTFS SPTrans). Linhas na última carga: **22.266**.

| Coluna | Tipo (MySQL) | Chave | Nulo | Descrição | Exemplo |
|---|---|---|---|---|---|
| `stop_id` | VARCHAR(20) | PK | não | ID GTFS do ponto de ônibus | 18848 |
| `nome` | VARCHAR(160) |  | não | Nome do ponto, lido em voz alta no alerta de descida | Clínicas |
| `nome_normalizado` | VARCHAR(160) |  | não | Nome sem acento/pontuação, para busca por voz | CLINICAS |
| `descricao` | VARCHAR(255) |  | sim | Referência/endereço do ponto, quando a SPTrans informa |  |
| `lat` | DOUBLE |  | não | WGS84; DOUBLE no MySQL | -23.554007 |
| `lon` | DOUBLE |  | não | WGS84; DOUBLE no MySQL | -46.671097 |
| `execucao_id` | VARCHAR(40) |  | não | Execução do pipeline que gravou a linha (FK lógica p/ carga_controle) | gtfs_20261113T202011192633_ae07f1c3 |

## `itinerario`

Sequência de paradas de cada letreiro; base do alerta de descida. Camada: curada (DAG 1. fonte GTFS SPTrans). Linhas na última carga: **99.031**.

| Coluna | Tipo (MySQL) | Chave | Nulo | Descrição | Exemplo |
|---|---|---|---|---|---|
| `letreiro_id` | VARCHAR(30) | PK, FK → letreiro.letreiro_id | não | Letreiro (linha+sentido) | 1012-10_0 |
| `ordem` | INTEGER | PK | não | stop_sequence GTFS | 1 |
| `stop_id` | VARCHAR(20) | FK → parada.stop_id | não | Parada nesta posição do trajeto | 301790 |
| `minutos_desde_inicio` | FLOAT |  | sim | Tempo previsto desde a 1a parada | 0.0 |
| `distancia_proxima_m` | FLOAT |  | sim | Distância em linha reta até a próxima parada | 412.4 |
| `execucao_id` | VARCHAR(40) |  | não | Execução do pipeline que gravou a linha (FK lógica p/ carga_controle) | gtfs_20261113T202011192633_ae07f1c3 |

## `frequencia`

Intervalo entre ônibus por faixa horária. Camada: curada (DAG 1. fonte GTFS SPTrans). Linhas na última carga: **40.353**.

| Coluna | Tipo (MySQL) | Chave | Nulo | Descrição | Exemplo |
|---|---|---|---|---|---|
| `letreiro_id` | VARCHAR(30) | PK, FK → letreiro.letreiro_id | não | Letreiro (linha+sentido) | 1012-10_0 |
| `hora_inicio` | VARCHAR(8) | PK | não | HH:MM:SS (pode passar de 24h no GTFS) | 00:00:00 |
| `hora_fim` | VARCHAR(8) |  | não | Fim da faixa horária (HH:MM:SS) | 00:59:00 |
| `intervalo_min` | FLOAT |  | não | Intervalo previsto entre ônibus, em minutos (headway_secs/60) | 20.0 |
| `execucao_id` | VARCHAR(40) |  | não | Execução do pipeline que gravou a linha (FK lógica p/ carga_controle) | gtfs_20261113T202011192633_ae07f1c3 |

## `evento_reconhecimento`

Uma leitura de letreiro feita pelo app (sem imagem e sem dado pessoal). Camada: operacional (escrita pelo MVP). Linhas na última carga: **500**.

| Coluna | Tipo (MySQL) | Chave | Nulo | Descrição | Exemplo |
|---|---|---|---|---|---|
| `evento_id` | VARCHAR(36) | PK | não | UUID gerado pelo app | 6c031199-972a-8469-1641-9f828b9d2434 |
| `ocorrido_em` | DATETIME |  | não | UTC | 2026-11-13 14:08:00.000000 |
| `sessao_hash` | VARCHAR(64) |  | não | SHA-256 de ID de sessão efêmero; sem dado pessoal | 3699fb66f87412213ff87c3a56d0d4852f326a4eb1740b43ec61e85e696f |
| `letreiro_alvo` | VARCHAR(30) |  | não | Letreiro escolhido pelo usuário | 2772-10_0 |
| `texto_ocr` | VARCHAR(160) |  | sim | Texto lido pela visão computacional | 2772-10 METRÔ PENHA |
| `letreiro_reconhecido` | VARCHAR(30) |  | sim | Melhor casamento OCR x tabela letreiro | 2772-10_0 |
| `confianca` | FLOAT |  | sim | 0..1 | 0.935 |
| `latencia_ms` | INTEGER |  | sim | Captura -> alerta | 902 |
| `alerta_emitido` | BOOL |  | não | O app avisou 'é o seu ônibus'? | 1 |
| `resultado` | VARCHAR(15) |  | não | acerto | erro | nao_confirmado | acerto |
| `condicao_luz` | VARCHAR(10) |  | sim | dia | noite | nao_informado | noite |
| `origem` | VARCHAR(15) |  | não | teste_campo | producao | simulado | simulado |

## `indicador_reconhecimento_diario`

Indicadores de impacto por dia e origem (DAG 2). Camada: curada (DAG 2). Linhas na última carga: **9**.

| Coluna | Tipo (MySQL) | Chave | Nulo | Descrição | Exemplo |
|---|---|---|---|---|---|
| `dia` | VARCHAR(10) | PK | não | AAAA-MM-DD | 2026-11-05 |
| `origem` | VARCHAR(15) | PK | não | teste_campo | producao | simulado | simulado |
| `total_eventos` | INTEGER |  | não | Leituras de letreiro no dia | 53 |
| `eventos_confirmados` | INTEGER |  | não | Leituras com resultado confirmado (acerto/erro) | 43 |
| `taxa_acerto` | FLOAT |  | sim | acertos / confirmados | 0.814 |
| `alertas_errados` | INTEGER |  | não | alerta para o ônibus errado (erro crítico) | 1 |
| `latencia_p50_ms` | FLOAT |  | sim | Mediana do tempo captura->alerta | 885.0 |
| `latencia_p95_ms` | FLOAT |  | sim | Percentil 95 do tempo captura->alerta | 1668.7999999999997 |
| `taxa_acerto_noite` | FLOAT |  | sim | Taxa de acerto só com condicao_luz = noite | 0.7647 |
| `calculado_em` | DATETIME |  | não | Quando o DAG 2 calculou (UTC) | 2026-11-12 01:37:10.181320 |

## `carga_controle`

Linhagem: cada execução do DAG 1. versão do feed e resultado. Camada: controle / linhagem. Linhas na última carga: **4**.

| Coluna | Tipo (MySQL) | Chave | Nulo | Descrição | Exemplo |
|---|---|---|---|---|---|
| `execucao_id` | VARCHAR(40) | PK | não | gtfs_<timestamp UTC>_<sha8> | gtfs_20261112T013707487421_457293b8 |
| `fonte` | VARCHAR(120) |  | não | Nome da fonte de dados | SPTrans GTFS (Mobility Database mdb-8) |
| `url` | VARCHAR(255) |  | não | De onde o arquivo foi baixado | https://files.mobilitydatabase.org/mdb-8/latest.zip |
| `sha256_arquivo` | VARCHAR(64) |  | não | Hash do zip: identifica a versão do feed | 457293b83e34e95e2f8d246dd22f9934525c5941d863d5f26b933cd9238f |
| `iniciada_em` | DATETIME |  | não | UTC | 2026-11-12 01:37:08.600798 |
| `finalizada_em` | DATETIME |  | sim | UTC | 2026-11-12 01:37:10.083106 |
| `status` | VARCHAR(15) |  | não | sucesso | falha | ignorada | sucesso |
| `linhas_carregadas` | TEXT |  | sim | JSON {tabela: qtd} | {"linha": 1365, "parada": 22270, "letreiro": 2268, "itinerar |
| `observacao` | TEXT |  | sim | Resumo da qualidade ou mensagem de erro | {"qualidade": {"total": 18, "falhas": 0, "avisos": 0}} |
