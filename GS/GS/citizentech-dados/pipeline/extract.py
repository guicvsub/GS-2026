"""Etapa 1 — Ingestão (camada raw).

Baixa o GTFS, calcula o SHA-256 (identifica a versão do feed) e guarda o zip
original intacto em data/raw/gtfs/<data>_<sha8>/. A camada raw nunca é
alterada: se uma transformação estiver errada, dá para reprocessar a partir dela.
"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from pipeline import config

log = logging.getLogger(__name__)


def _baixar(url: str, destino: Path, tentativas: int = 3, timeout: int = 120) -> None:
    ultimo_erro: Exception | None = None
    for n in range(1, tentativas + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "citizentech-pipeline/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp, open(destino, "wb") as f:
                shutil.copyfileobj(resp, f)
            return
        except Exception as e:  # rede instável: tenta de novo com espera crescente
            ultimo_erro = e
            log.warning("Falha ao baixar (tentativa %s/%s): %s", n, tentativas, e)
            time.sleep(5 * n)
    raise RuntimeError(f"Não foi possível baixar {url}") from ultimo_erro


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def extrair_gtfs(url: str | None = None, arquivo_local: str | None = None) -> dict:
    """Baixa (ou copia, se `arquivo_local`) o feed e devolve metadados da ingestão.

    O retorno é um dict simples (serializável) para trafegar via XCom no Airflow.
    """
    config.garantir_pastas()
    url = url or config.GTFS_URL
    tmp = config.RAW_DIR / "_download.zip"
    if arquivo_local:
        shutil.copyfile(arquivo_local, tmp)
        origem = Path(arquivo_local).resolve().as_uri()
    else:
        log.info("Baixando %s", url)
        _baixar(url, tmp)
        origem = url

    with zipfile.ZipFile(tmp) as z:  # valida que é um zip íntegro antes de aceitar
        ruim = z.testzip()
        if ruim:
            raise ValueError(f"Arquivo corrompido dentro do zip: {ruim}")
        nomes = set(z.namelist())

    faltando = [a for a in ("routes.txt", "trips.txt", "stops.txt", "stop_times.txt") if a not in nomes]
    if faltando:
        raise ValueError(f"GTFS sem arquivos obrigatórios: {faltando}")

    digest = sha256(tmp)
    agora = datetime.now(timezone.utc)
    pasta = config.RAW_DIR / "gtfs" / f"{agora:%Y%m%d}_{digest[:8]}"
    pasta.mkdir(parents=True, exist_ok=True)
    zip_final = pasta / "feed.zip"
    shutil.move(tmp, zip_final)

    meta = {
        "execucao_id": f"gtfs_{agora:%Y%m%dT%H%M%S%f}_{digest[:8]}",  # 35 chars, único por execução
        "fonte": config.GTFS_FONTE,
        "url": origem,
        "sha256": digest,
        "zip": str(zip_final),
        "baixado_em": agora.isoformat(),
        "tamanho_bytes": zip_final.stat().st_size,
        "arquivos": sorted(nomes),
    }
    (pasta / "_metadados.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Raw salvo em %s (%s bytes, sha256 %s)", config.rel(zip_final), meta["tamanho_bytes"], digest[:12])
    return meta
