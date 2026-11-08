"""API mínima do SemáforoFácil. Outras disciplinas plugam aqui:
- Visão: preenche contraste/tamanho_relativo/classificacao
- IA: preenche descricao/texto_relato
- RPA: lê relatos 'confirmado' e grava protocolo_156 + status 'registrado'
"""
import os
from typing import Optional

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

app = FastAPI(title="SemáforoFácil")
Instrumentator().instrument(app).expose(app)  # /metrics para o Prometheus


def conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


class RelatoIn(BaseModel):
    semaforo_id: int
    contraste: Optional[float] = None
    tamanho_relativo: Optional[float] = None
    classificacao: Optional[str] = None
    descricao: Optional[str] = None
    texto_relato: Optional[str] = None


@app.get("/health")
def health():
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/semaforos")
def listar_semaforos():
    with conn() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM semaforos ORDER BY id")
        return cur.fetchall()


@app.post("/relatos", status_code=201)
def criar_relato(r: RelatoIn):
    with conn() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """INSERT INTO relatos (semaforo_id, contraste, tamanho_relativo,
                   classificacao, descricao, texto_relato)
               VALUES (%s,%s,%s,%s,%s,%s) RETURNING *""",
            (r.semaforo_id, r.contraste, r.tamanho_relativo,
             r.classificacao, r.descricao, r.texto_relato),
        )
        return cur.fetchone()


@app.post("/relatos/{relato_id}/confirmar")
def confirmar(relato_id: int):
    """A pessoa confirma o texto: só então o robô pode registrar no 156."""
    with conn() as c, c.cursor() as cur:
        cur.execute("UPDATE relatos SET status='confirmado' WHERE id=%s AND status='rascunho'",
                    (relato_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "relato não encontrado ou já confirmado")
    return {"id": relato_id, "status": "confirmado"}


@app.get("/relatos")
def listar_relatos(status: Optional[str] = None):
    with conn() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if status:
            cur.execute("SELECT * FROM relatos WHERE status=%s ORDER BY id", (status,))
        else:
            cur.execute("SELECT * FROM relatos ORDER BY id")
        return cur.fetchall()


@app.get("/pontos-prioritarios")
def pontos():
    with conn() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""SELECT s.cruzamento, s.bairro, p.total_relatos, p.ultimo_relato
                       FROM pontos_prioritarios p JOIN semaforos s ON s.id=p.semaforo_id
                       ORDER BY p.total_relatos DESC""")
        return cur.fetchall()
