"""Exporta os dados em modelo estrela, para abrir no Power BI ou no Excel.

Uma tabela de factos (linhas de venda) e tabelas de dimensão (cliente,
produto, calendário). É o formato que o Power BI espera e evita ter de
tratar os relacionamentos à mão.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .analise import Analise
from .leitor import Dados

MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
            "agosto", "setembro", "outubro", "novembro", "dezembro"]
TRIMESTRES = {1: "T1", 2: "T1", 3: "T1", 4: "T2", 5: "T2", 6: "T2",
              7: "T3", 8: "T3", 9: "T3", 10: "T4", 11: "T4", 12: "T4"}


def calendario(inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
    dias = pd.date_range(inicio.normalize(), fim.normalize(), freq="D")
    c = pd.DataFrame({"data": dias})
    c["ano"] = c["data"].dt.year
    c["mes_numero"] = c["data"].dt.month
    c["mes"] = c["data"].dt.to_period("M").astype(str)
    c["mes_nome"] = c["mes_numero"].map(lambda m: MESES_PT[m - 1])
    c["trimestre"] = c["mes_numero"].map(TRIMESTRES)
    c["ano_mes_ordem"] = c["ano"] * 100 + c["mes_numero"]
    c["dia_semana"] = c["data"].dt.dayofweek + 1
    return c


def exportar(dados: Dados, analise: Analise, destino: Path) -> dict[str, Path]:
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)

    factos = dados.linhas[[
        "data", "mes", "documento", "tipo", "cliente_id", "produto_id",
        "categoria", "quantidade", "preco_unitario", "liquido", "taxa_iva",
    ]].copy()

    clientes = dados.clientes.merge(
        analise.clientes[["cliente_id", "estado", "primeira_compra", "ultima_compra",
                          "dias_sem_comprar", "intervalo_tipico", "valor_12m",
                          "valor_anual_estimado"]],
        on="cliente_id", how="left")

    produtos = dados.produtos.copy()
    inicio, fim = dados.documentos["data"].min(), dados.documentos["data"].max()

    ficheiros = {
        "factos_vendas.csv": factos,
        "dim_clientes.csv": clientes,
        "dim_produtos.csv": produtos,
        "dim_calendario.csv": calendario(inicio, fim),
        "resumo_mensal.csv": analise.evolucao,
        "clientes_em_risco.csv": analise.risco,
        "categorias.csv": analise.categorias,
        "preco_vs_volume.csv": analise.preco_volume,
        "controlo_saft.csv": dados.controlo,
    }
    saidas = {}
    for nome, tabela in ficheiros.items():
        caminho = destino / nome
        tabela.to_csv(caminho, index=False, encoding="utf-8-sig", sep=";", decimal=",")
        saidas[nome] = caminho
    return saidas
