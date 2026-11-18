"""DAG 1 — citizentech_gtfs_sptrans

Ingestão semanal do GTFS da SPTrans até a camada curada que o MVP consome.

criar_schema >> extrair >> versao_nova? >> transformar >> checar_qualidade >> carregar >> publicar_pacote_offline

- versao_nova? (short-circuit): se o sha256 do feed for igual ao da última carga
  boa, registra 'ignorada' em carga_controle e pula o resto. Rodar de novo não
  duplica nada (idempotente).
- checar_qualidade é um portão: se falhar, nada é carregado e o MVP continua
  com a última versão boa.
"""
from __future__ import annotations

from datetime import timedelta

import pendulum
from airflow.decorators import dag, task

from pipeline import extract, load, quality, serve, transform

PADRAO = {
    "owner": "equipe-citizentech",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id="citizentech_gtfs_sptrans",
    description="GTFS SPTrans -> raw -> staging (Parquet) -> MySQL curado + pacote offline do app",
    schedule="0 4 * * 1",  # segundas, 04:00 (horário de SP)
    start_date=pendulum.datetime(2026, 11, 1, tz="America/Sao_Paulo"),
    catchup=False,
    max_active_runs=1,
    default_args=PADRAO,
    tags=["citizentech", "gtfs", "dados"],
    doc_md=__doc__,
)
def citizentech_gtfs_sptrans():
    @task
    def criar_schema() -> None:
        load.criar_schema()

    @task
    def extrair() -> dict:
        return extract.extrair_gtfs()

    @task.short_circuit
    def versao_nova(meta: dict) -> bool:
        if load.versao_ja_carregada(meta["sha256"]):
            load.registrar_ignorada(meta)
            return False
        return True

    @task
    def transformar(meta: dict) -> dict:
        return transform.transformar_gtfs(meta)

    @task
    def checar_qualidade(caminhos: dict) -> dict:
        return quality.checar(caminhos)

    @task
    def carregar(meta: dict, caminhos: dict, relatorio: dict) -> dict:
        return load.carregar(meta, caminhos, relatorio)

    @task
    def publicar_pacote_offline(meta: dict, _contagem: dict) -> str:
        return serve.publicar_pacote_offline(meta)

    meta = extrair()
    gate = versao_nova(meta)
    caminhos = transformar(meta)
    relatorio = checar_qualidade(caminhos)
    contagem = carregar(meta, caminhos, relatorio)
    criar_schema() >> meta
    gate >> caminhos
    publicar_pacote_offline(meta, contagem)


citizentech_gtfs_sptrans()
