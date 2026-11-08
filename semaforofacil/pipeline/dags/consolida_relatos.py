"""DAG do Big Data: extrair -> tratar -> carregar.
Gera a tabela pontos_prioritarios que alimenta o painel."""
import os
from datetime import datetime

import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator


def _sql(*statements):
    with psycopg2.connect(os.environ["DATABASE_URL"]) as c, c.cursor() as cur:
        for s in statements:
            cur.execute(s)


def extrair():
    _sql("DROP TABLE IF EXISTS stg_relatos",
         "CREATE TABLE stg_relatos AS SELECT * FROM relatos WHERE status IN ('confirmado','registrado')")


def tratar():
    # remove relatos sem semáforo e normaliza a classificação
    _sql("DELETE FROM stg_relatos WHERE semaforo_id IS NULL",
         "UPDATE stg_relatos SET classificacao = lower(trim(classificacao))")


def carregar():
    _sql("TRUNCATE pontos_prioritarios",
         """INSERT INTO pontos_prioritarios (semaforo_id, total_relatos, ultimo_relato)
            SELECT semaforo_id, count(*), max(criado_em) FROM stg_relatos GROUP BY semaforo_id""")


with DAG("consolida_relatos", start_date=datetime(2026, 11, 1),
         schedule="@daily", catchup=False) as dag:
    t1 = PythonOperator(task_id="extrair", python_callable=extrair)
    t2 = PythonOperator(task_id="tratar", python_callable=tratar)
    t3 = PythonOperator(task_id="carregar", python_callable=carregar)
    t1 >> t2 >> t3
