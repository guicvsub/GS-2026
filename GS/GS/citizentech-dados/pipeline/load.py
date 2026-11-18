"""Etapa 4 — Carga na camada curada (MySQL) + registro de linhagem.

Estratégia: substituição completa por versão do feed, dentro de UMA transação.
Se qualquer insert falhar, o banco volta ao estado anterior e o MVP nunca vê
uma carga pela metade. A tabela carga_controle guarda qual versão (sha256)
está no ar, quando entrou e quantas linhas tem cada tabela.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine

from pipeline import config, schema

log = logging.getLogger(__name__)

_ENGINE: Engine | None = None


def engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        config.garantir_pastas()  # SQLite local precisa da pasta data/ existir
        _ENGINE = create_engine(config.DB_URL, pool_pre_ping=True, future=True)
    return _ENGINE


def criar_schema() -> None:
    schema.metadata.create_all(engine())


def _agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def versao_ja_carregada(sha256: str) -> bool:
    cc = schema.carga_controle
    with engine().connect() as conn:
        ultima = conn.execute(
            select(cc.c.sha256_arquivo).where(cc.c.status == "sucesso").order_by(cc.c.finalizada_em.desc()).limit(1)
        ).scalar()
    return ultima == sha256


def registrar_ignorada(meta: dict) -> None:
    with engine().begin() as conn:
        conn.execute(schema.carga_controle.insert().values(
            execucao_id=meta["execucao_id"], fonte=meta["fonte"], url=meta["url"][:255],
            sha256_arquivo=meta["sha256"], iniciada_em=_agora(), finalizada_em=_agora(),
            status="ignorada", observacao="Mesma versão do feed já carregada; nada a fazer.",
        ))


def _registros(df: pd.DataFrame) -> list[dict]:
    return df.astype(object).where(df.notna(), None).to_dict("records")


def carregar(meta: dict, caminhos: dict, relatorio_qualidade: dict | None = None) -> dict:
    criar_schema()
    iniciada = _agora()
    dfs = {nome: pd.read_parquet(p) for nome, p in caminhos.items()}
    # filhos primeiro na remoção, pais primeiro na inserção
    ordem_insert = ["linha", "parada", "letreiro", "itinerario", "frequencia"]
    contagem = {}
    try:
        with engine().begin() as conn:
            for nome in reversed(ordem_insert):
                conn.execute(schema.metadata.tables[nome].delete())
            for nome in ordem_insert:
                tabela = schema.metadata.tables[nome]
                regs = _registros(dfs[nome])
                for i in range(0, len(regs), 5000):
                    conn.execute(tabela.insert(), regs[i:i + 5000])
                n_banco = conn.execute(select(func.count()).select_from(tabela)).scalar_one()
                if n_banco != len(regs):  # reconciliação staging x banco
                    raise RuntimeError(f"{nome}: staging={len(regs)} banco={n_banco}")
                contagem[nome] = n_banco
                log.info("curated/%s: %s linhas carregadas", nome, n_banco)
            conn.execute(schema.carga_controle.insert().values(
                execucao_id=meta["execucao_id"], fonte=meta["fonte"], url=meta["url"][:255],
                sha256_arquivo=meta["sha256"], iniciada_em=iniciada, finalizada_em=_agora(),
                status="sucesso", linhas_carregadas=json.dumps(contagem),
                observacao=json.dumps({"qualidade": {k: relatorio_qualidade[k] for k in ("total", "falhas", "avisos")}})
                if relatorio_qualidade else None,
            ))
    except Exception as e:
        with engine().begin() as conn:
            conn.execute(schema.carga_controle.insert().values(
                execucao_id=meta["execucao_id"], fonte=meta["fonte"], url=meta["url"][:255],
                sha256_arquivo=meta["sha256"], iniciada_em=iniciada, finalizada_em=_agora(),
                status="falha", observacao=str(e)[:2000],
            ))
        raise
    return contagem
