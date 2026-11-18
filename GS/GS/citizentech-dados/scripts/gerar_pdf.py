"""Monta o PDF único de entrega (diagrama + dicionário + evidências).

    python -m scripts.gerar_documentacao   # antes: atualiza dicionário e consultas
    python -m scripts.gerar_pdf

Preencha antes (variáveis de ambiente ou edite aqui):
    ENTREGA_EQUIPE="Nome 1 (RM...), Nome 2 (RM...)"
    ENTREGA_REPO="https://github.com/<org>/<repo>"
    ENTREGA_VIDEO="https://..."     (vídeo curto ou pasta com prints do Airflow)

O PDF é impresso pelo Microsoft Edge/Chrome em modo headless (links clicáveis).
"""
from __future__ import annotations

import html
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from pipeline import config, quality

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"
GERADO = DOCS / "_gerado"
EVID = DOCS / "evidencias"

# Valores padrão da equipe (podem ser sobrescritos pelas variáveis de ambiente).
EQUIPE_PADRAO = (
    "Guilherme Santiago da Silva (RM552321), Gustavo Govea Soares (RM553842), "
    "Pedro Henrique Mello Silva Alves (RM554223), Gabriel Borba (RM553187)"
)
REPO_PADRAO = "https://github.com/guicvsub/GS-2026"
VIDEO_PADRAO = (
    "https://github.com/guicvsub/GS-2026/tree/master/GS/GS/citizentech-dados/docs/evidencias/prints_airflow"
)

LEGENDAS_PRINTS = {
    "00_airflow_login.png": "00 · Tela de login do Airflow (localhost:8080)",
    "01_airflow_home_dags.png": "01 · Visão geral dos dois DAGs ativos",
    "02_dag_gtfs_grid.png": "02 · Grid da DAG 1 — execução e reexecução (short-circuit)",
    "03_dag_gtfs_graph.png": "03 · Grafo de dependências da DAG 1",
    "04_dag_indicadores_grid.png": "04 · Grid da DAG 2 — indicadores de reconhecimento",
    "05_dag_indicadores_graph.png": "05 · Grafo da DAG 2",
    "06_dagruns_gtfs.png": "06 · Histórico de execuções da DAG 1",
    "07_dagruns_indicadores.png": "07 · Histórico de execuções da DAG 2",
}


def _prints() -> str:
    """Monta a seção de prints com as imagens embutidas no PDF."""
    arquivos = sorted((EVID / "prints_airflow").glob("*.png"))
    if not arquivos:
        return '<span class="preencher">[Nenhum print encontrado em docs/evidencias/prints_airflow/]</span>'
    blocos = []
    for arq in arquivos:
        legenda = LEGENDAS_PRINTS.get(arq.name, arq.stem.replace("_", " "))
        blocos.append(
            '<figure style="margin:10px 0;break-inside:avoid">'
            f'<img src="evidencias/prints_airflow/{arq.name}" alt="{html.escape(legenda)}" '
            'style="width:100%;border:1px solid #e2e8f0;border-radius:6px">'
            f'<figcaption style="font-size:9pt;color:#475569;margin-top:3px">{html.escape(legenda)}</figcaption>'
            "</figure>"
        )
    return "".join(blocos)


def _preencher(valor: str | None, texto: str, link: bool = False) -> str:
    if not valor:
        return f'<span class="preencher">[{texto}]</span>'
    v = html.escape(valor)
    return f'<a href="{v}">{v}</a>' if link else v


def _qualidade() -> tuple[str, str]:
    """Reexecuta as checagens sobre o staging mais recente (só leitura)."""
    pastas = sorted((p for p in config.STAGING_DIR.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime)
    ultima = pastas[-1]
    caminhos = {p.stem: str(p) for p in ultima.glob("*.parquet")}
    rel = quality.checar(caminhos)
    linhas = ["<table><thead><tr><th>Checagem</th><th>Crítica?</th><th>Resultado</th><th>Detalhe</th></tr></thead><tbody>"]
    for c in rel["checagens"]:
        res = '<span class="ok">OK</span>' if c["ok"] else '<span class="falha">FALHOU</span>'
        linhas.append(f"<tr><td><code>{c['checagem']}</code></td><td>{'sim' if c['critica'] else 'aviso'}</td>"
                      f"<td>{res}</td><td>{html.escape(c['detalhe'])}</td></tr>")
    linhas.append("</tbody></table>")
    resumo = f"<p>{rel['total']} checagens, {rel['falhas']} falhas críticas, {rel['avisos']} avisos.</p>"
    return resumo + "\n".join(linhas), ultima.name


def _kpis(contagem: dict) -> str:
    itens = [("linha", "linhas de ônibus"), ("letreiro", "letreiros (linha × sentido)"),
             ("parada", "paradas"), ("itinerario", "paradas em itinerários"), ("frequencia", "faixas de frequência")]
    return "".join(f'<div class="kpi"><div class="v">{contagem[k]:,}</div><div class="r">{r}</div></div>'.replace(",", ".")
                   for k, r in itens)


def _log(nome: str, max_linhas: int = 60) -> str:
    texto = (EVID / nome).read_text(encoding="utf-8").splitlines()
    return html.escape("\n".join(texto[:max_linhas]))


def _navegador() -> str:
    for c in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              shutil.which("chromium") or "", shutil.which("google-chrome") or "", shutil.which("microsoft-edge") or ""]:
        if c and Path(c).exists():
            return c
    raise RuntimeError("Edge/Chrome não encontrado para imprimir o PDF")


def main() -> None:
    contagem = json.loads((GERADO / "contagem.json").read_text(encoding="utf-8"))
    qualidade_html, execucao = _qualidade()
    meta_raw = sorted((config.RAW_DIR / "gtfs").glob("*/_metadados.json"))[-1]
    sha = json.loads(meta_raw.read_text(encoding="utf-8"))["sha256"]

    svg = (DOCS / "arquitetura.svg").read_text(encoding="utf-8")
    svg = svg.replace('width="1000" height="560"', "", 1)  # deixa o CSS controlar o tamanho

    prints = os.getenv("ENTREGA_PRINTS") or _prints()

    pagina = (DOCS / "entrega_template.html").read_text(encoding="utf-8")
    trocas = {
        "{{EQUIPE}}": _preencher(os.getenv("ENTREGA_EQUIPE") or EQUIPE_PADRAO, "nomes e RMs dos integrantes"),
        "{{REPO}}": _preencher(os.getenv("ENTREGA_REPO") or REPO_PADRAO, "link público do repositório", link=True),
        "{{VIDEO}}": _preencher(os.getenv("ENTREGA_VIDEO") or VIDEO_PADRAO, "link do vídeo ou dos prints", link=True),
        "{{DATA}}": datetime.now().strftime("%d/%m/%Y"),
        "{{KPIS}}": _kpis(contagem),
        "{{DIAGRAMA}}": svg,
        "{{SHA}}": sha[:16] + "…",
        "{{QUALIDADE}}": qualidade_html + f"<p>Execução: <code>{execucao}</code>.</p>",
        "{{DICIONARIO}}": (GERADO / "dicionario.html").read_text(encoding="utf-8"),
        "{{LOG1}}": _log("01_execucao_completa.log"),
        "{{LOG2}}": _log("02_reexecucao_idempotente.log"),
        "{{EVIDENCIAS}}": (GERADO / "evidencias.html").read_text(encoding="utf-8"),
        "{{PRINTS}}": prints,
    }
    for k, v in trocas.items():
        pagina = pagina.replace(k, v)
    saida_html = DOCS / "entrega_big_data.html"
    saida_html.write_text(pagina, encoding="utf-8")

    pdf = DOCS / "Entrega_BigData_CitizenTech.pdf"
    subprocess.run([_navegador(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", saida_html.resolve().as_uri()], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    print(f"PDF: {pdf.relative_to(RAIZ)} ({pdf.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
