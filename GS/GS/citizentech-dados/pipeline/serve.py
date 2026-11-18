"""Etapa 5 — Entrega ao produto.

O MVP lê o MySQL pela API. Além disso, o pipeline publica um pacote compacto
(data/serving/letreiros.json) que o app guarda no celular: assim a comparação
OCR x linha escolhida funciona mesmo sem internet no ponto de ônibus
(princípio "resiliente ao mundo real" do briefing).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import text

from pipeline import config
from pipeline.load import engine

log = logging.getLogger(__name__)


def publicar_pacote_offline(meta: dict) -> str:
    config.garantir_pastas()
    with engine().connect() as conn:
        let = pd.read_sql(
            text("SELECT l.letreiro_id, l.route_id, l.sentido, l.destino, l.texto_letreiro, l.texto_normalizado, "
            "li.nome AS nome_linha, li.cor_hex FROM letreiro l JOIN linha li ON li.route_id = l.route_id "
            "ORDER BY l.letreiro_id"),
            conn,
        )
    pacote = {
        "versao_feed": meta["sha256"][:12],
        "execucao_id": meta["execucao_id"],
        "fonte": meta["fonte"],
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(let),
        "letreiros": let.to_dict("records"),
    }
    destino = config.SERVING_DIR / "letreiros.json"
    destino.write_text(json.dumps(pacote, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log.info("Pacote offline: %s letreiros, %.0f KB em %s", len(let), destino.stat().st_size / 1024, config.rel(destino))
    return str(destino)  # caminho absoluto: usado por quem chama
