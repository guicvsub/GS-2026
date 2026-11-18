"""DAG 2 — Indicadores de impacto a partir dos eventos de reconhecimento.

O MVP grava um registro em evento_reconhecimento a cada leitura de letreiro
(sem imagem, sem localização, sem identificação do usuário). Este módulo agrega
por dia e por origem, para que o pitch mostre números medidos — e separa
'simulado' de 'teste_campo'/'producao' para nunca misturar os dois.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import text

from pipeline import schema
from pipeline.load import criar_schema, engine

log = logging.getLogger(__name__)


def _taxa(acertos: int, total: int) -> float | None:
    return round(acertos / total, 4) if total else None


def calcular_indicadores(dia_inicio: str | None = None) -> int:
    """Recalcula indicador_reconhecimento_diario (idempotente: apaga e reescreve os dias afetados)."""
    criar_schema()
    sql = "SELECT * FROM evento_reconhecimento"
    params = {}
    if dia_inicio:
        sql += " WHERE ocorrido_em >= :inicio"
        params["inicio"] = dia_inicio
    with engine().connect() as conn:
        ev = pd.read_sql(text(sql), conn, params=params, parse_dates=["ocorrido_em"])
    if ev.empty:
        log.info("Nenhum evento de reconhecimento no período; nada a calcular.")
        return 0

    ev["dia"] = ev["ocorrido_em"].dt.strftime("%Y-%m-%d")
    ev["alerta_emitido"] = ev["alerta_emitido"].astype(bool)
    linhas = []
    for (dia, origem), g in ev.groupby(["dia", "origem"]):
        conf = g[g["resultado"] != "nao_confirmado"]
        noite = conf[conf["condicao_luz"] == "noite"]
        lat = g["latencia_ms"].dropna()
        linhas.append({
            "dia": dia,
            "origem": origem,
            "total_eventos": len(g),
            "eventos_confirmados": len(conf),
            "taxa_acerto": _taxa(int((conf["resultado"] == "acerto").sum()), len(conf)),
            # o pior erro para o usuário: o app avisou "é o seu ônibus" e não era
            "alertas_errados": int((g["alerta_emitido"] & (g["resultado"] == "erro")).sum()),
            "latencia_p50_ms": float(lat.quantile(0.5)) if len(lat) else None,
            "latencia_p95_ms": float(lat.quantile(0.95)) if len(lat) else None,
            "taxa_acerto_noite": _taxa(int((noite["resultado"] == "acerto").sum()), len(noite)),
            "calculado_em": datetime.now(timezone.utc).replace(tzinfo=None),
        })
    ind = pd.DataFrame(linhas)
    tabela = schema.indicador_reconhecimento_diario
    with engine().begin() as conn:
        conn.execute(tabela.delete().where(tabela.c.dia.in_(ind["dia"].unique().tolist())))
        conn.execute(tabela.insert(), ind.astype(object).where(ind.notna(), None).to_dict("records"))
    log.info("Indicadores recalculados para %s dia(s)/origem(ns)", len(ind))
    return len(ind)
