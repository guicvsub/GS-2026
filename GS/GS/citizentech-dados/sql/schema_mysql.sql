-- Gerado por `python -m pipeline.schema`. Não editar à mão.
CREATE DATABASE IF NOT EXISTS citizentech CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE citizentech;

CREATE TABLE carga_controle (
	execucao_id VARCHAR(40) NOT NULL COMMENT 'gtfs_<timestamp UTC>_<sha8>', 
	fonte VARCHAR(120) NOT NULL COMMENT 'Nome da fonte de dados', 
	url VARCHAR(255) NOT NULL COMMENT 'De onde o arquivo foi baixado', 
	sha256_arquivo VARCHAR(64) NOT NULL COMMENT 'Hash do zip: identifica a versão do feed', 
	iniciada_em DATETIME NOT NULL COMMENT 'UTC', 
	finalizada_em DATETIME COMMENT 'UTC', 
	status VARCHAR(15) NOT NULL COMMENT 'sucesso | falha | ignorada', 
	linhas_carregadas TEXT COMMENT 'JSON {tabela: qtd}', 
	observacao TEXT COMMENT 'Resumo da qualidade ou mensagem de erro', 
	PRIMARY KEY (execucao_id)
)COMMENT='Linhagem: cada execução do DAG 1, versão do feed e resultado';

CREATE TABLE evento_reconhecimento (
	evento_id VARCHAR(36) NOT NULL COMMENT 'UUID gerado pelo app', 
	ocorrido_em DATETIME NOT NULL COMMENT 'UTC', 
	sessao_hash VARCHAR(64) NOT NULL COMMENT 'SHA-256 de ID de sessão efêmero; sem dado pessoal', 
	letreiro_alvo VARCHAR(30) NOT NULL COMMENT 'Letreiro escolhido pelo usuário', 
	texto_ocr VARCHAR(160) COMMENT 'Texto lido pela visão computacional', 
	letreiro_reconhecido VARCHAR(30) COMMENT 'Melhor casamento OCR x tabela letreiro', 
	confianca FLOAT COMMENT '0..1', 
	latencia_ms INTEGER COMMENT 'Captura -> alerta', 
	alerta_emitido BOOL NOT NULL COMMENT 'O app avisou ''é o seu ônibus''?', 
	resultado VARCHAR(15) NOT NULL COMMENT 'acerto | erro | nao_confirmado', 
	condicao_luz VARCHAR(10) COMMENT 'dia | noite | nao_informado', 
	origem VARCHAR(15) NOT NULL COMMENT 'teste_campo | producao | simulado', 
	PRIMARY KEY (evento_id)
)COMMENT='Uma leitura de letreiro feita pelo app (sem imagem e sem dado pessoal)';
CREATE INDEX ix_evento_data ON evento_reconhecimento (ocorrido_em);

CREATE TABLE indicador_reconhecimento_diario (
	dia VARCHAR(10) NOT NULL COMMENT 'AAAA-MM-DD', 
	origem VARCHAR(15) NOT NULL COMMENT 'teste_campo | producao | simulado', 
	total_eventos INTEGER NOT NULL COMMENT 'Leituras de letreiro no dia', 
	eventos_confirmados INTEGER NOT NULL COMMENT 'Leituras com resultado confirmado (acerto/erro)', 
	taxa_acerto FLOAT COMMENT 'acertos / confirmados', 
	alertas_errados INTEGER NOT NULL COMMENT 'alerta para o ônibus errado (erro crítico)', 
	latencia_p50_ms FLOAT COMMENT 'Mediana do tempo captura->alerta', 
	latencia_p95_ms FLOAT COMMENT 'Percentil 95 do tempo captura->alerta', 
	taxa_acerto_noite FLOAT COMMENT 'Taxa de acerto só com condicao_luz = noite', 
	calculado_em DATETIME NOT NULL COMMENT 'Quando o DAG 2 calculou (UTC)', 
	PRIMARY KEY (dia, origem)
)COMMENT='Indicadores de impacto por dia e origem (DAG 2)';

CREATE TABLE linha (
	route_id VARCHAR(20) NOT NULL COMMENT 'ID GTFS da linha, ex. 8000-10', 
	numero VARCHAR(10) NOT NULL COMMENT 'Parte numérica do letreiro, ex. 8000', 
	sufixo VARCHAR(5) COMMENT 'Sufixo após o hífen, ex. 10', 
	nome VARCHAR(160) NOT NULL COMMENT 'Nome longo: terminal A - terminal B', 
	tipo_transporte SMALLINT NOT NULL COMMENT 'route_type GTFS (3 = ônibus)', 
	cor_hex VARCHAR(6) COMMENT 'Cor oficial da linha (RGB hex), usada na interface', 
	execucao_id VARCHAR(40) NOT NULL COMMENT 'Execução do pipeline que gravou a linha (FK lógica p/ carga_controle)', 
	PRIMARY KEY (route_id)
)COMMENT='Linhas de ônibus da SPTrans (fonte: GTFS)';

CREATE TABLE parada (
	stop_id VARCHAR(20) NOT NULL COMMENT 'ID GTFS do ponto de ônibus', 
	nome VARCHAR(160) NOT NULL COMMENT 'Nome do ponto, lido em voz alta no alerta de descida', 
	nome_normalizado VARCHAR(160) NOT NULL COMMENT 'Nome sem acento/pontuação, para busca por voz', 
	descricao VARCHAR(255) COMMENT 'Referência/endereço do ponto, quando a SPTrans informa', 
	lat FLOAT(53) NOT NULL COMMENT 'WGS84; DOUBLE no MySQL', 
	lon FLOAT(53) NOT NULL COMMENT 'WGS84; DOUBLE no MySQL', 
	execucao_id VARCHAR(40) NOT NULL COMMENT 'Execução do pipeline que gravou a linha (FK lógica p/ carga_controle)', 
	PRIMARY KEY (stop_id)
)COMMENT='Pontos de ônibus com coordenadas';

CREATE TABLE letreiro (
	letreiro_id VARCHAR(30) NOT NULL COMMENT 'route_id + ''_'' + sentido', 
	route_id VARCHAR(20) NOT NULL COMMENT 'Linha à qual o letreiro pertence', 
	sentido SMALLINT NOT NULL COMMENT 'direction_id GTFS (0 ida, 1 volta)', 
	destino VARCHAR(120) NOT NULL COMMENT 'trip_headsign, como aparece no ônibus', 
	texto_letreiro VARCHAR(160) NOT NULL COMMENT 'numero-sufixo + destino', 
	texto_normalizado VARCHAR(160) NOT NULL COMMENT 'Sem acento, maiúsculo, sem pontuação', 
	trip_id_referencia VARCHAR(40) NOT NULL COMMENT 'Viagem GTFS usada como modelo do sentido', 
	execucao_id VARCHAR(40) NOT NULL COMMENT 'Execução do pipeline que gravou a linha (FK lógica p/ carga_controle)', 
	PRIMARY KEY (letreiro_id), 
	FOREIGN KEY(route_id) REFERENCES linha (route_id)
)COMMENT='Texto do painel do ônibus por sentido; vocabulário do OCR';
CREATE INDEX ix_letreiro_texto ON letreiro (texto_normalizado);

CREATE TABLE frequencia (
	letreiro_id VARCHAR(30) NOT NULL COMMENT 'Letreiro (linha+sentido)', 
	hora_inicio VARCHAR(8) NOT NULL COMMENT 'HH:MM:SS (pode passar de 24h no GTFS)', 
	hora_fim VARCHAR(8) NOT NULL COMMENT 'Fim da faixa horária (HH:MM:SS)', 
	intervalo_min FLOAT NOT NULL COMMENT 'Intervalo previsto entre ônibus, em minutos (headway_secs/60)', 
	execucao_id VARCHAR(40) NOT NULL COMMENT 'Execução do pipeline que gravou a linha (FK lógica p/ carga_controle)', 
	PRIMARY KEY (letreiro_id, hora_inicio), 
	FOREIGN KEY(letreiro_id) REFERENCES letreiro (letreiro_id)
)COMMENT='Intervalo entre ônibus por faixa horária';

CREATE TABLE itinerario (
	letreiro_id VARCHAR(30) NOT NULL COMMENT 'Letreiro (linha+sentido)', 
	ordem INTEGER NOT NULL COMMENT 'stop_sequence GTFS', 
	stop_id VARCHAR(20) NOT NULL COMMENT 'Parada nesta posição do trajeto', 
	minutos_desde_inicio FLOAT COMMENT 'Tempo previsto desde a 1a parada', 
	distancia_proxima_m FLOAT COMMENT 'Distância em linha reta até a próxima parada', 
	execucao_id VARCHAR(40) NOT NULL COMMENT 'Execução do pipeline que gravou a linha (FK lógica p/ carga_controle)', 
	PRIMARY KEY (letreiro_id, ordem), 
	FOREIGN KEY(letreiro_id) REFERENCES letreiro (letreiro_id), 
	FOREIGN KEY(stop_id) REFERENCES parada (stop_id)
)COMMENT='Sequência de paradas de cada letreiro; base do alerta de descida';
CREATE INDEX ix_itinerario_stop ON itinerario (stop_id);
