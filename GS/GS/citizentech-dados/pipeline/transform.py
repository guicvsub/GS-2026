"""Etapa 2 — Tratamento (camada staging, Parquet).

Lê os .txt do GTFS direto do zip raw, corrige codificação, padroniza tipos,
normaliza textos e monta as tabelas que o MVP usa:

- linha       : uma linha de ônibus (ex. 8000-10)
- letreiro    : o que aparece no painel do ônibus, por sentido. É o vocabulário
                que a visão computacional usa para casar o texto do OCR.
- parada      : pontos de ônibus com coordenadas
- itinerario  : sequência de paradas de cada letreiro (base do alerta de descida)
- frequencia  : intervalo entre ônibus por faixa horária (estimativa de espera
                quando não há dado em tempo real)
"""
from __future__ import annotations

import io
import logging
import math
import re
import unicodedata
import zipfile
from pathlib import Path

import pandas as pd

from pipeline import config

log = logging.getLogger(__name__)

_NAO_ALFANUM = re.compile(r"[^A-Z0-9]+")


def normalizar(texto: str | None) -> str:
    """'Term. Jd. Britânia' -> 'TERM JD BRITANIA' (igual ao que o OCR produz após limpeza)."""
    if texto is None or (isinstance(texto, float) and math.isnan(texto)):
        return ""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return _NAO_ALFANUM.sub(" ", sem_acento.upper()).strip()


def decodificar(conteudo: bytes) -> tuple[str, str]:
    """O GTFS da SPTrans mistura UTF-8 e Windows-1252 entre arquivos. Detecta por arquivo."""
    try:
        return conteudo.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return conteudo.decode("cp1252"), "cp1252"


def ler_gtfs(zip_path: str | Path, nome: str, obrigatorio: bool = True) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as z:
        if nome not in z.namelist():
            if obrigatorio:
                raise FileNotFoundError(nome)
            return pd.DataFrame()
        texto, enc = decodificar(z.read(nome))
    df = pd.read_csv(io.StringIO(texto), dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    df = df.apply(lambda s: s.str.strip())
    log.info("%s: %s linhas (%s)", nome, len(df), enc)
    return df


def hhmmss_para_seg(valor: str) -> float | None:
    """GTFS permite 25:10:00 (viagem que passa da meia-noite), por isso não usamos datetime."""
    if not valor:
        return None
    h, m, s = (int(x) for x in valor.split(":"))
    return h * 3600 + m * 60 + s


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def montar_linha(routes: pd.DataFrame) -> pd.DataFrame:
    df = routes.drop_duplicates("route_id").copy()
    partes = df["route_short_name"].where(df["route_short_name"] != "", df["route_id"]).str.split("-", n=1, expand=True)
    df["numero"] = partes[0]
    df["sufixo"] = partes[1] if partes.shape[1] > 1 else None
    df["sufixo"] = df["sufixo"].where(df["sufixo"].notna() & (df["sufixo"] != ""), None)
    df["nome"] = df["route_long_name"].str.replace(r"\s+", " ", regex=True)
    df["tipo_transporte"] = pd.to_numeric(df["route_type"], errors="coerce").fillna(3).astype(int)
    df["cor_hex"] = df.get("route_color", pd.Series(index=df.index, dtype=str)).str.upper().replace("", None)
    return df[["route_id", "numero", "sufixo", "nome", "tipo_transporte", "cor_hex"]].reset_index(drop=True)


def montar_letreiro(trips: pd.DataFrame, linha: pd.DataFrame) -> pd.DataFrame:
    t = trips.copy()
    t["sentido"] = pd.to_numeric(t.get("direction_id", "0").replace("", "0"), errors="coerce").fillna(0).astype(int)
    # Uma viagem de referência por linha+sentido (a SPTrans publica uma por sentido
    # e modela os horários em frequencies.txt).
    t = t.sort_values(["route_id", "sentido", "trip_id"]).drop_duplicates(["route_id", "sentido"])
    t = t.merge(linha[["route_id", "numero", "sufixo"]], on="route_id", how="inner")
    rotulo = t["numero"] + t["sufixo"].map(lambda s: f"-{s}" if s else "")
    t["destino"] = t["trip_headsign"].str.replace(r"\s+", " ", regex=True)
    t["texto_letreiro"] = (rotulo + " " + t["destino"]).str.strip()
    t["texto_normalizado"] = t["texto_letreiro"].map(normalizar)
    t["letreiro_id"] = t["route_id"] + "_" + t["sentido"].astype(str)
    t = t.rename(columns={"trip_id": "trip_id_referencia"})
    return t[["letreiro_id", "route_id", "sentido", "destino", "texto_letreiro", "texto_normalizado",
              "trip_id_referencia"]].reset_index(drop=True)


def montar_parada(stops: pd.DataFrame) -> pd.DataFrame:
    df = stops.drop_duplicates("stop_id").copy()
    df["nome"] = df["stop_name"].str.replace(r"\s+", " ", regex=True)
    df["nome_normalizado"] = df["nome"].map(normalizar)
    df["descricao"] = df.get("stop_desc", "").replace("", None)
    df["lat"] = pd.to_numeric(df["stop_lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["stop_lon"], errors="coerce")
    descartadas = df["lat"].isna() | df["lon"].isna()
    if descartadas.any():
        log.warning("Descartando %s paradas sem coordenada válida", int(descartadas.sum()))
    df = df[~descartadas]
    return df[["stop_id", "nome", "nome_normalizado", "descricao", "lat", "lon"]].reset_index(drop=True)


def montar_itinerario(stop_times: pd.DataFrame, letreiro: pd.DataFrame, parada: pd.DataFrame) -> pd.DataFrame:
    ref = letreiro[["letreiro_id", "trip_id_referencia"]].rename(columns={"trip_id_referencia": "trip_id"})
    st = stop_times.merge(ref, on="trip_id", how="inner")
    st["ordem"] = pd.to_numeric(st["stop_sequence"], errors="coerce").astype("Int64")
    st = st.dropna(subset=["ordem"]).sort_values(["letreiro_id", "ordem"])
    st["seg"] = st["arrival_time"].map(hhmmss_para_seg)
    st["minutos_desde_inicio"] = (st["seg"] - st.groupby("letreiro_id")["seg"].transform("min")) / 60.0

    coords = parada.set_index("stop_id")[["lat", "lon"]]
    st = st.join(coords, on="stop_id")
    st["lat_prox"] = st.groupby("letreiro_id")["lat"].shift(-1)
    st["lon_prox"] = st.groupby("letreiro_id")["lon"].shift(-1)
    st["distancia_proxima_m"] = [
        round(haversine_m(a, b, c, d), 1) if pd.notna(a) and pd.notna(c) else None
        for a, b, c, d in zip(st["lat"], st["lon"], st["lat_prox"], st["lon_prox"])
    ]
    st = st.drop_duplicates(["letreiro_id", "ordem"])
    st["ordem"] = st["ordem"].astype(int)
    return st[["letreiro_id", "ordem", "stop_id", "minutos_desde_inicio", "distancia_proxima_m"]].reset_index(drop=True)


def montar_frequencia(freq: pd.DataFrame, letreiro: pd.DataFrame) -> pd.DataFrame:
    if freq.empty:
        return pd.DataFrame(columns=["letreiro_id", "hora_inicio", "hora_fim", "intervalo_min"])
    ref = letreiro[["letreiro_id", "trip_id_referencia"]].rename(columns={"trip_id_referencia": "trip_id"})
    f = freq.merge(ref, on="trip_id", how="inner")
    f["intervalo_min"] = pd.to_numeric(f["headway_secs"], errors="coerce") / 60.0
    f = f.rename(columns={"start_time": "hora_inicio", "end_time": "hora_fim"})
    f = f.dropna(subset=["intervalo_min"]).drop_duplicates(["letreiro_id", "hora_inicio"])
    return f[["letreiro_id", "hora_inicio", "hora_fim", "intervalo_min"]].reset_index(drop=True)


def transformar_gtfs(meta: dict) -> dict:
    """Gera os Parquet de staging a partir do zip raw. Devolve {tabela: caminho}."""
    zip_path = meta["zip"]
    routes = ler_gtfs(zip_path, "routes.txt")
    trips = ler_gtfs(zip_path, "trips.txt")
    stops = ler_gtfs(zip_path, "stops.txt")
    stop_times = ler_gtfs(zip_path, "stop_times.txt")
    freq = ler_gtfs(zip_path, "frequencies.txt", obrigatorio=False)

    tabelas = {}
    tabelas["linha"] = montar_linha(routes)
    tabelas["letreiro"] = montar_letreiro(trips, tabelas["linha"])
    tabelas["parada"] = montar_parada(stops)
    tabelas["itinerario"] = montar_itinerario(stop_times, tabelas["letreiro"], tabelas["parada"])
    tabelas["frequencia"] = montar_frequencia(freq, tabelas["letreiro"])

    destino = config.STAGING_DIR / meta["execucao_id"]
    destino.mkdir(parents=True, exist_ok=True)
    caminhos = {}
    for nome, df in tabelas.items():
        df = df.copy()
        df["execucao_id"] = meta["execucao_id"]
        caminho = destino / f"{nome}.parquet"
        df.to_parquet(caminho, index=False)
        caminhos[nome] = str(caminho)
        log.info("staging/%s: %s linhas", nome, len(df))
    return caminhos
