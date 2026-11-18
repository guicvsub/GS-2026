"""Executa o pipeline sem Airflow (mesmas funções que os DAGs chamam).

Útil para desenvolvimento, CI e para quem avalia sem Docker:

    python -m pipeline.run_local gtfs                # ingestão completa
    python -m pipeline.run_local gtfs --zip feed.zip # usa um zip já baixado
    python -m pipeline.run_local simular --n 500     # eventos simulados (origem=simulado)
    python -m pipeline.run_local indicadores         # DAG 2
    python -m pipeline.run_local tudo
"""
from __future__ import annotations

import argparse
import json
import logging

from pipeline import config, extract, load, metrics, quality, serve, simulacao, transform


def pipeline_gtfs(zip_local: str | None = None, forcar: bool = False) -> dict:
    load.criar_schema()
    meta = extract.extrair_gtfs(arquivo_local=zip_local)
    if not forcar and load.versao_ja_carregada(meta["sha256"]):
        load.registrar_ignorada(meta)
        logging.info("Versão %s já está no banco; carga ignorada.", meta["sha256"][:12])
        return {"status": "ignorada", "execucao_id": meta["execucao_id"]}
    caminhos = transform.transformar_gtfs(meta)
    rel = quality.checar(caminhos)
    contagem = load.carregar(meta, caminhos, rel)
    pacote = serve.publicar_pacote_offline(meta)
    return {"status": "sucesso", "execucao_id": meta["execucao_id"], "linhas": contagem,
            "qualidade": {k: rel[k] for k in ("total", "falhas", "avisos")}, "pacote_offline": config.rel(pacote)}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("etapa", choices=["gtfs", "simular", "indicadores", "tudo"])
    ap.add_argument("--zip", help="zip GTFS local em vez de baixar")
    ap.add_argument("--forcar", action="store_true", help="recarrega mesmo se a versão já estiver no banco")
    ap.add_argument("--n", type=int, default=500)
    a = ap.parse_args()

    saida = {}
    if a.etapa in ("gtfs", "tudo"):
        saida["gtfs"] = pipeline_gtfs(a.zip, a.forcar)
    if a.etapa in ("simular", "tudo"):
        saida["simulados"] = simulacao.gerar(n=a.n)
    if a.etapa in ("indicadores", "tudo"):
        saida["indicadores"] = metrics.calcular_indicadores()
    print(json.dumps(saida, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
