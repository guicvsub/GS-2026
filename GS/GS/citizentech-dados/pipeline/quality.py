"""Etapa 3 — Portão de qualidade.

Roda sobre o staging ANTES de tocar no banco. Se uma checagem crítica falhar,
a tarefa falha no Airflow e o MVP continua lendo a última carga boa.
"""
from __future__ import annotations

import json
import logging

import pandas as pd

from pipeline import config

log = logging.getLogger(__name__)


class FalhaQualidade(Exception):
    pass


def checar(caminhos: dict) -> dict:
    t = {nome: pd.read_parquet(p) for nome, p in caminhos.items()}
    resultados: list[dict] = []

    def registra(nome: str, ok: bool, detalhe: str, critica: bool = True) -> None:
        resultados.append({"checagem": nome, "ok": bool(ok), "critica": critica, "detalhe": detalhe})

    # 1. Volume mínimo (feed truncado / zip errado)
    for tabela, minimo in config.MIN_LINHAS.items():
        n = len(t[tabela])
        registra(f"volume_{tabela}", n >= minimo, f"{n} linhas (mínimo {minimo})")

    # 2. Chaves primárias únicas
    pks = {"linha": ["route_id"], "letreiro": ["letreiro_id"], "parada": ["stop_id"],
           "itinerario": ["letreiro_id", "ordem"], "frequencia": ["letreiro_id", "hora_inicio"]}
    for tabela, cols in pks.items():
        dup = int(t[tabela].duplicated(cols).sum())
        registra(f"pk_unica_{tabela}", dup == 0, f"{dup} duplicadas")

    # 3. Integridade referencial
    fk = [("letreiro", "route_id", "linha", "route_id"),
          ("itinerario", "letreiro_id", "letreiro", "letreiro_id"),
          ("itinerario", "stop_id", "parada", "stop_id"),
          ("frequencia", "letreiro_id", "letreiro", "letreiro_id")]
    for filha, col, mae, col_mae in fk:
        orfaos = int((~t[filha][col].isin(t[mae][col_mae])).sum())
        registra(f"fk_{filha}_{col}", orfaos == 0, f"{orfaos} órfãos")

    # 4. Campos que o app lê em voz alta não podem vir vazios
    vazios = int((t["letreiro"]["texto_normalizado"].str.len() == 0).sum())
    registra("letreiro_texto_preenchido", vazios == 0, f"{vazios} letreiros sem texto")
    sem_destino = int((t["letreiro"]["destino"].str.len() == 0).sum())
    registra("letreiro_destino_preenchido", sem_destino == 0, f"{sem_destino} sem destino", critica=False)

    # 5. Coordenadas dentro da Grande São Paulo
    b = config.BBOX_SP
    p = t["parada"]
    fora = int((~p["lat"].between(b["lat_min"], b["lat_max"]) | ~p["lon"].between(b["lon_min"], b["lon_max"])).sum())
    registra("parada_dentro_bbox", fora / max(len(p), 1) < 0.01, f"{fora} paradas fora da RMSP")

    # 6. Itinerário coerente: tempo não pode andar para trás
    it = t["itinerario"].sort_values(["letreiro_id", "ordem"])
    regressoes = int((it.groupby("letreiro_id")["minutos_desde_inicio"].diff() < 0).sum())
    registra("itinerario_tempo_crescente", regressoes == 0, f"{regressoes} regressões", critica=False)

    # 7. Cobertura: todo letreiro deveria ter itinerário (senão não há alerta de descida)
    sem_it = int((~t["letreiro"]["letreiro_id"].isin(it["letreiro_id"])).sum())
    registra("letreiro_com_itinerario", sem_it / max(len(t["letreiro"]), 1) < 0.05,
             f"{sem_it} letreiros sem itinerário")

    falhas = [r for r in resultados if r["critica"] and not r["ok"]]
    avisos = [r for r in resultados if not r["critica"] and not r["ok"]]
    for r in resultados:
        nivel = logging.INFO if r["ok"] else (logging.ERROR if r["critica"] else logging.WARNING)
        log.log(nivel, "[%s] %s: %s", "OK" if r["ok"] else "FALHOU", r["checagem"], r["detalhe"])

    relatorio = {"total": len(resultados), "falhas": len(falhas), "avisos": len(avisos), "checagens": resultados}
    if falhas:
        raise FalhaQualidade(json.dumps(falhas, ensure_ascii=False))
    return relatorio
