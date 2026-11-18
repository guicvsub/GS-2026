"""Gera a documentação a partir do schema e do banco carregado (fonte única de verdade).

    python -m scripts.gerar_documentacao

Saídas:
  docs/dicionario_de_dados.md        dicionário com tipo MySQL, chave, nulidade, descrição e exemplo real
  docs/evidencias/03_consultas.txt   consultas de verificação sobre o banco carregado
  docs/_gerado/*.html                trechos usados no PDF de entrega (docs/entrega_big_data.html)
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects import mysql

from pipeline import matching, schema
from pipeline.load import engine

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"
GERADO = DOCS / "_gerado"
ORDEM = ["linha", "letreiro", "parada", "itinerario", "frequencia",
         "evento_reconhecimento", "indicador_reconhecimento_diario", "carga_controle"]
CAMADA = {"evento_reconhecimento": "operacional (escrita pelo MVP)",
          "indicador_reconhecimento_diario": "curada (DAG 2)",
          "carga_controle": "controle / linhagem"}


def _tipo(col) -> str:
    t = col.type.compile(dialect=mysql.dialect())
    return "DOUBLE" if t == "FLOAT(53)" else t


def _chave(col) -> str:
    partes = []
    if col.primary_key:
        partes.append("PK")
    for fk in col.foreign_keys:
        partes.append(f"FK → {fk.target_fullname}")
    return ", ".join(partes)


def _exemplos(conn) -> dict[str, dict]:
    ex = {}
    for nome in ORDEM:
        df = pd.read_sql(text(f"SELECT * FROM {nome} LIMIT 50"), conn)
        ex[nome] = {}
        for c in df.columns:
            v = df[c].dropna()
            v = v[v.astype(str) != ""]
            ex[nome][c] = "" if v.empty else str(v.iloc[0])[:60]
    return ex


def main() -> None:
    GERADO.mkdir(parents=True, exist_ok=True)
    (DOCS / "evidencias").mkdir(parents=True, exist_ok=True)
    with engine().connect() as conn:
        contagem = {n: conn.execute(text(f"SELECT COUNT(*) FROM {n}")).scalar() for n in ORDEM}
        exemplos = _exemplos(conn)

        # ---------------- dicionário (Markdown + HTML)
        md = ["# Dicionário de dados — camada curada (MySQL `citizentech`)", "",
              "Gerado automaticamente por `python -m scripts.gerar_documentacao` a partir de "
              "`pipeline/schema.py` e do banco carregado. Exemplos são valores reais da última carga.", ""]
        h = []
        for nome in ORDEM:
            t = schema.metadata.tables[nome]
            camada = CAMADA.get(nome, "curada (DAG 1, fonte GTFS SPTrans)")
            md += [f"## `{nome}`", "", f"{t.comment}. Camada: {camada}. Linhas na última carga: **{contagem[nome]:,}**.".replace(",", "."), "",
                   "| Coluna | Tipo (MySQL) | Chave | Nulo | Descrição | Exemplo |", "|---|---|---|---|---|---|"]
            h.append(f'<section class="tabela"><h3><code>{nome}</code> <span class="n">{contagem[nome]:,} linhas</span></h3>'
                     .replace(",", "."))
            h.append(f'<p>{html.escape(t.comment)}. <em>Camada: {camada}.</em></p>')
            h.append("<table><thead><tr><th>Coluna</th><th>Tipo</th><th>Chave</th><th>Nulo</th><th>Descrição</th><th>Exemplo</th></tr></thead><tbody>")
            for col in t.columns:
                ex = exemplos[nome].get(col.name, "")
                nulo = "sim" if col.nullable else "não"
                md.append(f"| `{col.name}` | {_tipo(col)} | {_chave(col)} | {nulo} | {col.comment or ''} | {ex.replace('|', '/')} |")
                h.append(f"<tr><td><code>{col.name}</code></td><td>{_tipo(col)}</td><td>{html.escape(_chave(col))}</td>"
                         f"<td>{nulo}</td><td>{html.escape(col.comment or '')}</td><td class='ex'>{html.escape(ex)}</td></tr>")
            h.append("</tbody></table></section>")
            md.append("")
        (DOCS / "dicionario_de_dados.md").write_text("\n".join(md), encoding="utf-8")
        (GERADO / "dicionario.html").write_text("\n".join(h), encoding="utf-8")

        # ---------------- consultas de verificação
        consultas = {
            "Linhagem (carga_controle)":
                "SELECT execucao_id, status, sha256_arquivo, linhas_carregadas FROM carga_controle ORDER BY iniciada_em",
            "Letreiros da linha 8000-10 (o que o OCR precisa reconhecer)":
                "SELECT letreiro_id, texto_letreiro, texto_normalizado FROM letreiro WHERE route_id = '8000-10'",
            "Alerta de descida: primeiras paradas do 8000-10 sentido 0, com nome e tempo previsto":
                "SELECT i.ordem, p.nome, ROUND(i.minutos_desde_inicio, 1) AS min, i.distancia_proxima_m "
                "FROM itinerario i JOIN parada p ON p.stop_id = i.stop_id "
                "WHERE i.letreiro_id = '8000-10_0' ORDER BY i.ordem LIMIT 6",
            "Espera estimada sem tempo real: intervalo do 8000-10 sentido 0 por faixa":
                "SELECT hora_inicio, hora_fim, intervalo_min FROM frequencia "
                "WHERE letreiro_id = '8000-10_0' ORDER BY hora_inicio LIMIT 6",
            "Linhas que passam numa parada (ex.: a 1a parada do 8000-10)":
                "SELECT l.texto_letreiro FROM itinerario i JOIN letreiro l ON l.letreiro_id = i.letreiro_id "
                "WHERE i.stop_id = (SELECT stop_id FROM itinerario WHERE letreiro_id = '8000-10_0' AND ordem = 1) "
                "ORDER BY 1 LIMIT 8",
            "Indicadores diários (origem = simulado: NÃO são resultados medidos)":
                "SELECT dia, origem, total_eventos, taxa_acerto, alertas_errados, latencia_p50_ms, taxa_acerto_noite "
                "FROM indicador_reconhecimento_diario ORDER BY dia",
        }
        saida, h_ev = [], []
        for titulo, sql in consultas.items():
            df = pd.read_sql(text(sql), conn)
            saida += [f"-- {titulo}", sql, df.to_string(index=False), ""]
            h_ev.append(f"<h4>{html.escape(titulo)}</h4><pre class='sql'>{html.escape(sql)}</pre>"
                        + df.to_html(index=False, border=0, classes="res", na_rep="—"))

        # ---------------- contrato com a visão computacional
        letreiros = pd.read_sql(text("SELECT letreiro_id, texto_normalizado FROM letreiro"), conn).to_dict("records")
        testes = ["8OOO-1O TERM. LAPA", "1O6A-1O METRO SANTANA", "107T-10 TERM PINHEIROS",
                  "PCA RAMOS DE AZEVEDO"]
        linhas_m = ["-- Casamento OCR -> letreiro (pipeline/matching.py) sobre os letreiros reais carregados"]
        rows = []
        for tx in testes:
            m = matching.casar(tx, letreiros)
            linhas_m.append(f"{tx!r:28} -> {m['letreiro_id']:11} score={m['score']} ambiguo={m['ambiguo']}"
                            + (f" (empata com {m['alternativa']})" if m["ambiguo"] else ""))
            rows.append((tx, m["letreiro_id"], m["score"],
                         f"sim, empata com {m['alternativa']}: app não alerta" if m["ambiguo"] else "não"))
        saida += linhas_m
        h_ev.append("<h4>Contrato com a visão computacional: texto do OCR → letreiro real</h4>"
                    + pd.DataFrame(rows, columns=["texto lido pelo OCR (com ruído)", "letreiro casado", "score", "ambíguo?"])
                    .to_html(index=False, border=0, classes="res"))
    (DOCS / "evidencias" / "03_consultas.txt").write_text("\n".join(saida), encoding="utf-8")
    (GERADO / "evidencias.html").write_text("\n".join(h_ev), encoding="utf-8")
    (GERADO / "contagem.json").write_text(json.dumps(contagem), encoding="utf-8")
    print(json.dumps(contagem, indent=2))


if __name__ == "__main__":
    main()
