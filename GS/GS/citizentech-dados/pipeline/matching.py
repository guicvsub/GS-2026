"""Contrato com a Visão Computacional: casar o texto do OCR com um letreiro real.

O OCR devolve algo como "8OOO-1O TERM LAPA" (O no lugar de 0, ruído, corte).
Esta função compara com o vocabulário que o pipeline produz (tabela letreiro
ou data/serving/letreiros.json) e devolve o melhor candidato, a pontuação e se
o resultado é AMBÍGUO.

Ambiguidade é real nos dados da SPTrans: 8000-1 e 8000-10 vão para o mesmo
destino; se o OCR não leu o sufixo, as duas pontuam igual. Nesses casos o app
não deve dizer "é o seu ônibus" — deve pedir nova leitura ou avisar a dúvida
(IA responsável: na dúvida, não afirmar).
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from pipeline.transform import normalizar

# Trocas típicas de OCR em painéis de LED quando o contexto é numérico
_TROCAS_NUM = str.maketrans({"O": "0", "D": "0", "I": "1", "L": "1", "S": "5", "B": "8", "Z": "2"})
_NUMERO = re.compile(r"\b([0-9A-Z]{3,4})\s*-?\s*([0-9A-Z]{1,2})\b")
MARGEM_AMBIGUIDADE = 0.03


def _chave_numero(texto_norm: str) -> str | None:
    """Código da linha em forma canônica: '8OOO 1O ...' -> '8000 10'.

    Aplica as trocas letra->dígito dos DOIS lados (OCR e cadastro), porque há
    códigos reais terminando em letra (106A, 118L, 2002D): assim '118L' e '1181'
    caem na mesma chave e o empate vira ambiguidade, não acerto falso.
    """
    for m in _NUMERO.finditer(texto_norm):
        # exige ao menos 2 dígitos reais para não confundir palavras ("TERM LA") com número
        if sum(c.isdigit() for c in m.group(1) + m.group(2)) >= 2:
            return f"{m.group(1).translate(_TROCAS_NUM)} {m.group(2).translate(_TROCAS_NUM)}"
    return None


def pontuar(texto_ocr: str, letreiros: list[dict]) -> list[dict]:
    """Todos os letreiros com score, do melhor para o pior."""
    alvo = normalizar(texto_ocr)
    if not alvo:
        return []
    num = _chave_numero(alvo)
    res = []
    for l in letreiros:
        cand = l["texto_normalizado"]
        score = SequenceMatcher(None, alvo, cand).ratio()
        if num and _chave_numero(cand) == num:  # código completo bate: sinal mais forte
            score = 0.6 + 0.4 * score
        res.append({**l, "score": round(score, 3)})
    return sorted(res, key=lambda r: r["score"], reverse=True)


def casar(texto_ocr: str, letreiros: list[dict]) -> dict | None:
    """Melhor letreiro + `ambiguo` (segundo colocado a menos de MARGEM_AMBIGUIDADE) + `alternativa`."""
    ranking = pontuar(texto_ocr, letreiros)
    if not ranking:
        return None
    melhor = ranking[0]
    segundo = ranking[1] if len(ranking) > 1 else None
    ambiguo = bool(segundo and melhor["score"] - segundo["score"] < MARGEM_AMBIGUIDADE)
    return {**melhor, "ambiguo": ambiguo, "alternativa": segundo["letreiro_id"] if ambiguo else None}
