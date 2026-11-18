"""DAG 2 — citizentech_indicadores_reconhecimento

Diariamente agrega os eventos de reconhecimento gravados pelo MVP em
indicador_reconhecimento_diario (taxa de acerto, alertas errados, latência
p50/p95, acerto à noite), separado por origem.

Recalcula os últimos 7 dias a cada execução para incluir eventos que chegam
atrasados (celular sem rede envia depois).

Parâmetro `simular` (padrão False): gera 500 eventos com origem='simulado'
antes do cálculo, só para demonstração. Ver pipeline/simulacao.py.
"""
from __future__ import annotations

from datetime import timedelta

import pendulum
from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.operators.python import get_current_context

from pipeline import metrics, simulacao


@dag(
    dag_id="citizentech_indicadores_reconhecimento",
    description="Eventos de reconhecimento do app -> indicadores diários de impacto",
    schedule="30 1 * * *",
    start_date=pendulum.datetime(2026, 11, 1, tz="America/Sao_Paulo"),
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "equipe-citizentech", "retries": 1, "retry_delay": timedelta(minutes=5)},
    params={"simular": Param(False, type="boolean", description="Gerar eventos simulados (demo)")},
    tags=["citizentech", "indicadores", "dados"],
    doc_md=__doc__,
)
def citizentech_indicadores_reconhecimento():
    @task
    def simular_se_pedido() -> int:
        ctx = get_current_context()
        if ctx["params"].get("simular"):
            return simulacao.gerar(n=500)
        return 0

    @task
    def calcular(_gerados: int) -> int:
        ctx = get_current_context()
        inicio = ctx["data_interval_end"].subtract(days=7).in_timezone("UTC").strftime("%Y-%m-%d")
        return metrics.calcular_indicadores(dia_inicio=inicio)

    calcular(simular_se_pedido())


citizentech_indicadores_reconhecimento()
