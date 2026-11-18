"""Testes das regras de transformação, qualidade e do contrato com a visão computacional.

Usa um mini-GTFS sintético (fixture) para rodar em segundos e sem internet.
"""
from __future__ import annotations

import importlib
import zipfile

import pandas as pd
import pytest

from pipeline import matching, transform


ROUTES = """route_id,agency_id,route_short_name,route_long_name,route_type,route_color
8000-10,1,8000-10,Term. Lapa - Pça. Ramos de Azevedo,3,509e2f
875A-10,1,875A-10,Perdizes - Metrô Butantã,3,
"""
TRIPS = """route_id,service_id,trip_id,trip_headsign,direction_id,shape_id
8000-10,USD,8000-10-0,Pça. Ramos de Azevedo,0,1
8000-10,USD,8000-10-1,Term. Lapa,1,2
875A-10,USD,875A-10-0,Metrô Butantã,0,3
"""
STOPS = """stop_id,stop_name,stop_desc,stop_lat,stop_lon
1,Term. Lapa,,-23.5225,-46.7031
2,Rua Clélia,,-23.5260,-46.6950
3,Pça. Ramos,,-23.5450,-46.6370
4,Sem coordenada,,,
"""
STOP_TIMES = """trip_id,arrival_time,departure_time,stop_id,stop_sequence
8000-10-0,07:00:00,07:00:00,1,1
8000-10-0,07:05:00,07:05:00,2,2
8000-10-0,07:30:00,07:30:00,3,3
8000-10-1,23:50:00,23:50:00,3,1
8000-10-1,24:10:00,24:10:00,1,2
875A-10-0,08:00:00,08:00:00,2,1
"""
FREQ = """trip_id,start_time,end_time,headway_secs
8000-10-0,07:00:00,07:59:00,600
8000-10-1,23:00:00,23:59:00,1800
"""


@pytest.fixture()
def mini_gtfs(tmp_path):
    z = tmp_path / "feed.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("routes.txt", ROUTES.encode("cp1252"))  # simula arquivo em Windows-1252
        f.writestr("trips.txt", TRIPS)
        f.writestr("stops.txt", STOPS)
        f.writestr("stop_times.txt", STOP_TIMES)
        f.writestr("frequencies.txt", FREQ)
    return z


@pytest.fixture()
def tabelas(mini_gtfs):
    z = mini_gtfs
    linha = transform.montar_linha(transform.ler_gtfs(z, "routes.txt"))
    letreiro = transform.montar_letreiro(transform.ler_gtfs(z, "trips.txt"), linha)
    parada = transform.montar_parada(transform.ler_gtfs(z, "stops.txt"))
    itin = transform.montar_itinerario(transform.ler_gtfs(z, "stop_times.txt"), letreiro, parada)
    freq = transform.montar_frequencia(transform.ler_gtfs(z, "frequencies.txt"), letreiro)
    return linha, letreiro, parada, itin, freq


def test_normalizar():
    assert transform.normalizar("Term. Jd. Britânia") == "TERM JD BRITANIA"
    assert transform.normalizar("  Metrô   Butantã ") == "METRO BUTANTA"
    assert transform.normalizar(None) == ""


def test_decodifica_cp1252(mini_gtfs):
    routes = transform.ler_gtfs(mini_gtfs, "routes.txt")
    assert "Pça. Ramos de Azevedo" in routes["route_long_name"].iloc[0]


def test_linha_numero_sufixo_e_cor(tabelas):
    linha = tabelas[0].set_index("route_id")
    assert linha.loc["8000-10", "numero"] == "8000"
    assert linha.loc["8000-10", "sufixo"] == "10"
    assert linha.loc["8000-10", "cor_hex"] == "509E2F"
    assert linha.loc["875A-10", "cor_hex"] is None


def test_letreiro_por_sentido(tabelas):
    letreiro = tabelas[1].set_index("letreiro_id")
    assert set(letreiro.index) == {"8000-10_0", "8000-10_1", "875A-10_0"}
    assert letreiro.loc["8000-10_1", "texto_letreiro"] == "8000-10 Term. Lapa"
    assert letreiro.loc["8000-10_1", "texto_normalizado"] == "8000 10 TERM LAPA"


def test_parada_sem_coordenada_descartada(tabelas):
    assert "4" not in tabelas[2]["stop_id"].tolist()


def test_itinerario_tempo_passa_meia_noite(tabelas):
    it = tabelas[3]
    volta = it[it["letreiro_id"] == "8000-10_1"].sort_values("ordem")
    assert volta["minutos_desde_inicio"].tolist() == [0.0, 20.0]  # 23:50 -> 24:10
    ida = it[it["letreiro_id"] == "8000-10_0"].sort_values("ordem")
    assert ida["distancia_proxima_m"].iloc[0] > 0
    assert pd.isna(ida["distancia_proxima_m"].iloc[-1])  # última parada não tem próxima


def test_frequencia_em_minutos(tabelas):
    f = tabelas[4].set_index("letreiro_id")
    assert f.loc["8000-10_0", "intervalo_min"] == 10.0


def test_matching_ocr_com_ruido(tabelas):
    letreiros = tabelas[1].to_dict("records")
    m = matching.casar("8OOO-1O TERM. LAPA", letreiros)  # O no lugar de 0
    assert m["letreiro_id"] == "8000-10_1"
    m2 = matching.casar("875A 10 METRO BUTANTA", letreiros)
    assert m2["letreiro_id"] == "875A-10_0"
    assert matching.casar("", letreiros) is None
    assert m["ambiguo"] is False


def test_matching_sinaliza_ambiguidade():
    # caso real da SPTrans: 8000-1 e 8000-10 vão para o mesmo destino
    letreiros = [
        {"letreiro_id": "8000-1_0", "texto_normalizado": "8000 1 PCA RAMOS DE AZEVEDO"},
        {"letreiro_id": "8000-10_0", "texto_normalizado": "8000 10 PCA RAMOS DE AZEVEDO"},
        {"letreiro_id": "106A-10_1", "texto_normalizado": "106A 10 METRO SANTANA"},
    ]
    sem_sufixo = matching.casar("PCA RAMOS DE AZEVEDO", letreiros)
    assert sem_sufixo["ambiguo"] is True and sem_sufixo["alternativa"] is not None
    completo = matching.casar("8OOO-1O PCA RAMOS DE AZEVEDO", letreiros)
    assert completo["letreiro_id"] == "8000-10_0" and completo["ambiguo"] is False
    letra = matching.casar("1O6A-1O METRO SANTANA", letreiros)  # código com letra final
    assert letra["letreiro_id"] == "106A-10_1"


def test_pipeline_ponta_a_ponta_sqlite(mini_gtfs, tmp_path, monkeypatch):
    """Extrai -> transforma -> carga -> idempotência, num banco SQLite temporário."""
    monkeypatch.setenv("CITIZENTECH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("CITIZENTECH_DB_URL", f"sqlite:///{(tmp_path / 't.db').as_posix()}")
    from pipeline import config, extract, load, run_local
    for mod in (config, extract, load):
        importlib.reload(mod)
    monkeypatch.setattr(config, "MIN_LINHAS", {"linha": 1, "letreiro": 1, "parada": 1, "itinerario": 1})
    run_local = importlib.reload(run_local)

    r1 = run_local.pipeline_gtfs(zip_local=str(mini_gtfs))
    assert r1["status"] == "sucesso"
    assert r1["linhas"] == {"linha": 2, "parada": 3, "letreiro": 3, "itinerario": 6, "frequencia": 2}
    r2 = run_local.pipeline_gtfs(zip_local=str(mini_gtfs))
    assert r2["status"] == "ignorada"  # mesma versão do feed não recarrega
