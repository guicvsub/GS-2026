"""Gerador de eventos de reconhecimento SIMULADOS (origem = 'simulado').

Por que existe: o DAG de indicadores precisa ser demonstrado antes dos testes
de campo com usuários. O briefing aceita dados simulados desde que a geração
seja justificada e documentada. Premissas (todas configuráveis e explícitas):

- letreiros sorteados entre os REAIS da tabela letreiro (não inventamos linhas);
- cada evento é um ônibus passando; 30% das vezes é a linha que o usuário espera;
- quando o OCR erra e passa outro ônibus, 20% das vezes confunde com a linha
  esperada (é o caso de alerta errado, o mais grave para o usuário);
- acerto de 90% de dia e 70% à noite (painel LED com reflexo/baixo contraste),
  números de referência para OCR em cena, a serem substituídos pelos testes reais;
- 15% das leituras sem confirmação do usuário;
- latência ~ lognormal com mediana ~900 ms;
- o app só alerta quando a confiança passa de 0,75.

Esses eventos NUNCA devem ser apresentados como resultado medido: o indicador
sai separado por origem e o pitch deve citar só 'teste_campo'.
"""
from __future__ import annotations

import hashlib
import logging
import random
import uuid
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import text

from pipeline import schema
from pipeline.load import criar_schema, engine

log = logging.getLogger(__name__)

PREMISSAS = {
    "acerto_dia": 0.90,
    "acerto_noite": 0.70,
    "prop_noite": 0.35,
    "prop_onibus_alvo": 0.30,
    "prop_confusao_com_alvo": 0.20,
    "prop_nao_confirmado": 0.15,
    "limiar_alerta": 0.75,
    "latencia_mediana_ms": 900,
}


def gerar(n: int = 500, dias: int = 7, semente: int = 42, fim: datetime | None = None) -> int:
    criar_schema()
    rnd = random.Random(semente)
    with engine().connect() as conn:
        let = pd.read_sql(text("SELECT letreiro_id, texto_letreiro FROM letreiro"), conn)
    if let.empty:
        raise RuntimeError("Tabela letreiro vazia: rode o pipeline GTFS antes de simular eventos.")
    ids = let["letreiro_id"].tolist()
    textos = dict(zip(let["letreiro_id"], let["texto_letreiro"]))
    fim = fim or datetime.utcnow().replace(microsecond=0)
    p = PREMISSAS
    eventos = []
    for _ in range(n):
        # cada evento = um ônibus passando pelo ponto enquanto o usuário espera a linha "alvo"
        alvo = rnd.choice(ids)
        chegando = alvo if rnd.random() < p["prop_onibus_alvo"] else rnd.choice(ids)
        noite = rnd.random() < p["prop_noite"]
        acertou = rnd.random() < (p["acerto_noite"] if noite else p["acerto_dia"])
        if acertou:
            reconhecido = chegando
        else:  # leitura errada; às vezes confunde justamente com a linha esperada
            reconhecido = alvo if (chegando != alvo and rnd.random() < p["prop_confusao_com_alvo"]) else rnd.choice(ids)
        conf = rnd.uniform(0.78, 0.99) if acertou else rnd.uniform(0.3, 0.9)
        # o app só diz "é o seu ônibus" se a leitura bater com o alvo e passar do limiar
        alerta = reconhecido == alvo and conf >= p["limiar_alerta"]
        resultado = "nao_confirmado" if rnd.random() < p["prop_nao_confirmado"] else ("acerto" if acertou else "erro")
        sessao = hashlib.sha256(f"sim-{rnd.randint(1, 60)}".encode()).hexdigest()
        eventos.append({
            "evento_id": str(uuid.UUID(int=rnd.getrandbits(128))),
            "ocorrido_em": fim - timedelta(seconds=rnd.randint(0, dias * 86400)),
            "sessao_hash": sessao,
            "letreiro_alvo": alvo,
            "texto_ocr": textos[reconhecido].upper(),
            "letreiro_reconhecido": reconhecido,
            "confianca": round(conf, 3),
            "latencia_ms": int(rnd.lognormvariate(0, 0.35) * p["latencia_mediana_ms"]),
            "alerta_emitido": bool(alerta),
            "resultado": resultado,
            "condicao_luz": "noite" if noite else "dia",
            "origem": "simulado",
        })
    tabela = schema.evento_reconhecimento
    with engine().begin() as conn:
        conn.execute(tabela.delete().where(tabela.c.origem == "simulado"))
        conn.execute(tabela.insert(), eventos)
    log.info("%s eventos simulados gravados (semente %s)", n, semente)
    return n
