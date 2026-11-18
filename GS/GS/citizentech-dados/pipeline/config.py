"""Configuração central do pipeline.

Tudo que muda entre ambientes (local, Airflow em Docker, CI) vem de variáveis
de ambiente. Nenhuma credencial fica no código: a URL do banco é lida de
CITIZENTECH_DB_URL (ver .env.example).
"""
from __future__ import annotations

import os
from pathlib import Path

# Raiz de dados: data/raw (bruto), data/staging (Parquet tratado), data/serving (exports p/ o app)
DATA_DIR = Path(os.getenv("CITIZENTECH_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
RAW_DIR = DATA_DIR / "raw"
STAGING_DIR = DATA_DIR / "staging"
SERVING_DIR = DATA_DIR / "serving"
INPUT_DIR = DATA_DIR / "input"

# Banco curado consumido pelo MVP. Local: SQLite. Docker/CI: MySQL.
# Ex.: mysql+pymysql://citizentech:***@mysql:3306/citizentech
DB_URL = os.getenv("CITIZENTECH_DB_URL", f"sqlite:///{(DATA_DIR / 'citizentech.db').as_posix()}")

# Fonte 1: GTFS estático da SPTrans (São Paulo), espelhado pelo Mobility Database
# (catálogo mdb-8). O link oficial da SPTrans exige cadastro; o espelho é público
# e é atualizado sempre que a SPTrans publica uma versão nova.
GTFS_URL = os.getenv("GTFS_URL", "https://files.mobilitydatabase.org/mdb-8/latest.zip")
GTFS_FONTE = os.getenv("GTFS_FONTE", "SPTrans GTFS (Mobility Database mdb-8)")

# Arquivos GTFS que o pipeline usa. shapes.txt (60 MB) fica só na camada raw:
# o MVP não desenha o traçado, só precisa da sequência de paradas.
GTFS_ARQUIVOS = [
    "agency.txt",
    "routes.txt",
    "trips.txt",
    "stops.txt",
    "stop_times.txt",
    "frequencies.txt",
    "calendar.txt",
]

# Caixa geográfica da Região Metropolitana de São Paulo (checagem de qualidade).
BBOX_SP = {"lat_min": -24.1, "lat_max": -23.1, "lon_min": -47.2, "lon_max": -46.0}

# Quantidade mínima esperada por tabela: protege contra feed truncado/corrompido.
MIN_LINHAS = {
    "linha": 500,
    "letreiro": 500,
    "parada": 5000,
    "itinerario": 10000,
}


def rel(caminho) -> str:
    """Caminho relativo à pasta data/ para logs (não expõe diretórios da máquina)."""
    try:
        return "data/" + Path(caminho).resolve().relative_to(DATA_DIR.resolve()).as_posix()
    except ValueError:
        return Path(caminho).name


def garantir_pastas() -> None:
    for p in (RAW_DIR, STAGING_DIR, SERVING_DIR, INPUT_DIR):
        p.mkdir(parents=True, exist_ok=True)
