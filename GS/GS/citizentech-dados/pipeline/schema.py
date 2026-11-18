"""Modelo físico da camada curada (o "contrato" entre o pipeline e o MVP).

Definido com SQLAlchemy Core para rodar igual em MySQL (Docker/CI) e SQLite
(execução local). O DDL de MySQL equivalente é exportado em sql/schema_mysql.sql
por `python -m pipeline.schema`.

O dicionário de dados detalhado está em docs/dicionario_de_dados.md.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    SmallInteger,
    String,
    Table,
    Text,
)

metadata = MetaData()

# ---------------------------------------------------------------- referência (GTFS)
linha = Table(
    "linha",
    metadata,
    Column("route_id", String(20), primary_key=True, comment="ID GTFS da linha, ex. 8000-10"),
    Column("numero", String(10), nullable=False, comment="Parte numérica do letreiro, ex. 8000"),
    Column("sufixo", String(5), nullable=True, comment="Sufixo após o hífen, ex. 10"),
    Column("nome", String(160), nullable=False, comment="Nome longo: terminal A - terminal B"),
    Column("tipo_transporte", SmallInteger, nullable=False, comment="route_type GTFS (3 = ônibus)"),
    Column("cor_hex", String(6), nullable=True, comment="Cor oficial da linha (RGB hex), usada na interface"),
    Column("execucao_id", String(40), nullable=False, comment="Execução do pipeline que gravou a linha (FK lógica p/ carga_controle)"),
)

letreiro = Table(
    "letreiro",
    metadata,
    Column("letreiro_id", String(30), primary_key=True, comment="route_id + '_' + sentido"),
    Column("route_id", String(20), ForeignKey("linha.route_id"), nullable=False, comment="Linha à qual o letreiro pertence"),
    Column("sentido", SmallInteger, nullable=False, comment="direction_id GTFS (0 ida, 1 volta)"),
    Column("destino", String(120), nullable=False, comment="trip_headsign, como aparece no ônibus"),
    Column("texto_letreiro", String(160), nullable=False, comment="numero-sufixo + destino"),
    Column("texto_normalizado", String(160), nullable=False, comment="Sem acento, maiúsculo, sem pontuação"),
    Column("trip_id_referencia", String(40), nullable=False, comment="Viagem GTFS usada como modelo do sentido"),
    Column("execucao_id", String(40), nullable=False, comment="Execução do pipeline que gravou a linha (FK lógica p/ carga_controle)"),
    Index("ix_letreiro_texto", "texto_normalizado"),
)

parada = Table(
    "parada",
    metadata,
    Column("stop_id", String(20), primary_key=True, comment="ID GTFS do ponto de ônibus"),
    Column("nome", String(160), nullable=False, comment="Nome do ponto, lido em voz alta no alerta de descida"),
    Column("nome_normalizado", String(160), nullable=False, comment="Nome sem acento/pontuação, para busca por voz"),
    Column("descricao", String(255), nullable=True, comment="Referência/endereço do ponto, quando a SPTrans informa"),
    Column("lat", Float(precision=53), nullable=False, comment="WGS84; DOUBLE no MySQL"),
    Column("lon", Float(precision=53), nullable=False, comment="WGS84; DOUBLE no MySQL"),
    Column("execucao_id", String(40), nullable=False, comment="Execução do pipeline que gravou a linha (FK lógica p/ carga_controle)"),
)

itinerario = Table(
    "itinerario",
    metadata,
    Column("letreiro_id", String(30), ForeignKey("letreiro.letreiro_id"), primary_key=True, comment="Letreiro (linha+sentido)"),
    Column("ordem", Integer, primary_key=True, comment="stop_sequence GTFS"),
    Column("stop_id", String(20), ForeignKey("parada.stop_id"), nullable=False, comment="Parada nesta posição do trajeto"),
    Column("minutos_desde_inicio", Float, nullable=True, comment="Tempo previsto desde a 1a parada"),
    Column("distancia_proxima_m", Float, nullable=True, comment="Distância em linha reta até a próxima parada"),
    Column("execucao_id", String(40), nullable=False, comment="Execução do pipeline que gravou a linha (FK lógica p/ carga_controle)"),
    Index("ix_itinerario_stop", "stop_id"),
)

frequencia = Table(
    "frequencia",
    metadata,
    Column("letreiro_id", String(30), ForeignKey("letreiro.letreiro_id"), primary_key=True, comment="Letreiro (linha+sentido)"),
    Column("hora_inicio", String(8), primary_key=True, comment="HH:MM:SS (pode passar de 24h no GTFS)"),
    Column("hora_fim", String(8), nullable=False, comment="Fim da faixa horária (HH:MM:SS)"),
    Column("intervalo_min", Float, nullable=False, comment="Intervalo previsto entre ônibus, em minutos (headway_secs/60)"),
    Column("execucao_id", String(40), nullable=False, comment="Execução do pipeline que gravou a linha (FK lógica p/ carga_controle)"),
)

# ---------------------------------------------------------------- operacional (escrito pelo MVP)
evento_reconhecimento = Table(
    "evento_reconhecimento",
    metadata,
    Column("evento_id", String(36), primary_key=True, comment="UUID gerado pelo app"),
    Column("ocorrido_em", DateTime, nullable=False, comment="UTC"),
    Column("sessao_hash", String(64), nullable=False, comment="SHA-256 de ID de sessão efêmero; sem dado pessoal"),
    Column("letreiro_alvo", String(30), nullable=False, comment="Letreiro escolhido pelo usuário"),
    Column("texto_ocr", String(160), nullable=True, comment="Texto lido pela visão computacional"),
    Column("letreiro_reconhecido", String(30), nullable=True, comment="Melhor casamento OCR x tabela letreiro"),
    Column("confianca", Float, nullable=True, comment="0..1"),
    Column("latencia_ms", Integer, nullable=True, comment="Captura -> alerta"),
    Column("alerta_emitido", Boolean, nullable=False, comment="O app avisou 'é o seu ônibus'?"),
    Column("resultado", String(15), nullable=False, comment="acerto | erro | nao_confirmado"),
    Column("condicao_luz", String(10), nullable=True, comment="dia | noite | nao_informado"),
    Column("origem", String(15), nullable=False, comment="teste_campo | producao | simulado"),
    Index("ix_evento_data", "ocorrido_em"),
)

indicador_reconhecimento_diario = Table(
    "indicador_reconhecimento_diario",
    metadata,
    Column("dia", String(10), primary_key=True, comment="AAAA-MM-DD"),
    Column("origem", String(15), primary_key=True, comment="teste_campo | producao | simulado"),
    Column("total_eventos", Integer, nullable=False, comment="Leituras de letreiro no dia"),
    Column("eventos_confirmados", Integer, nullable=False, comment="Leituras com resultado confirmado (acerto/erro)"),
    Column("taxa_acerto", Float, nullable=True, comment="acertos / confirmados"),
    Column("alertas_errados", Integer, nullable=False, comment="alerta para o ônibus errado (erro crítico)"),
    Column("latencia_p50_ms", Float, nullable=True, comment="Mediana do tempo captura->alerta"),
    Column("latencia_p95_ms", Float, nullable=True, comment="Percentil 95 do tempo captura->alerta"),
    Column("taxa_acerto_noite", Float, nullable=True, comment="Taxa de acerto só com condicao_luz = noite"),
    Column("calculado_em", DateTime, nullable=False, comment="Quando o DAG 2 calculou (UTC)"),
)

# ---------------------------------------------------------------- linhagem / controle
carga_controle = Table(
    "carga_controle",
    metadata,
    Column("execucao_id", String(40), primary_key=True, comment="gtfs_<timestamp UTC>_<sha8>"),
    Column("fonte", String(120), nullable=False, comment="Nome da fonte de dados"),
    Column("url", String(255), nullable=False, comment="De onde o arquivo foi baixado"),
    Column("sha256_arquivo", String(64), nullable=False, comment="Hash do zip: identifica a versão do feed"),
    Column("iniciada_em", DateTime, nullable=False, comment="UTC"),
    Column("finalizada_em", DateTime, nullable=True, comment="UTC"),
    Column("status", String(15), nullable=False, comment="sucesso | falha | ignorada"),
    Column("linhas_carregadas", Text, nullable=True, comment="JSON {tabela: qtd}"),
    Column("observacao", Text, nullable=True, comment="Resumo da qualidade ou mensagem de erro"),
)

COMENTARIOS_TABELA = {
    "linha": "Linhas de ônibus da SPTrans (fonte: GTFS)",
    "letreiro": "Texto do painel do ônibus por sentido; vocabulário do OCR",
    "parada": "Pontos de ônibus com coordenadas",
    "itinerario": "Sequência de paradas de cada letreiro; base do alerta de descida",
    "frequencia": "Intervalo entre ônibus por faixa horária",
    "evento_reconhecimento": "Uma leitura de letreiro feita pelo app (sem imagem e sem dado pessoal)",
    "indicador_reconhecimento_diario": "Indicadores de impacto por dia e origem (DAG 2)",
    "carga_controle": "Linhagem: cada execução do DAG 1, versão do feed e resultado",
}
for _nome, _coment in COMENTARIOS_TABELA.items():
    metadata.tables[_nome].comment = _coment

TABELAS_GTFS = ["linha", "letreiro", "parada", "itinerario", "frequencia"]


def exportar_ddl_mysql() -> str:
    from sqlalchemy.dialects import mysql
    from sqlalchemy.schema import CreateIndex, CreateTable

    partes = ["-- Gerado por `python -m pipeline.schema`. Não editar à mão.",
              "CREATE DATABASE IF NOT EXISTS citizentech CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;",
              "USE citizentech;", ""]
    dialeto = mysql.dialect()
    for tabela in metadata.sorted_tables:
        partes.append(str(CreateTable(tabela).compile(dialect=dialeto)).strip() + ";")
        for idx in tabela.indexes:
            partes.append(str(CreateIndex(idx).compile(dialect=dialeto)).strip() + ";")
        partes.append("")
    return "\n".join(partes)


if __name__ == "__main__":
    from pathlib import Path

    destino = Path(__file__).resolve().parents[1] / "sql" / "schema_mysql.sql"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(exportar_ddl_mysql(), encoding="utf-8")
    print(f"DDL escrito em {destino}")
