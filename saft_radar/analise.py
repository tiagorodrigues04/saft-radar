"""Análise das vendas: KPIs, clientes em risco, categorias, preço vs volume.

Tudo o que sai daqui responde a uma pergunta que o dono da empresa faz:
"quem me está a fugir, o que está a cair, e onde é que eu mexo primeiro?"
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .leitor import Dados

# Um cliente com menos do que isto por ano não justifica uma ação comercial.
VALOR_MINIMO_ACAO = 400.0


@dataclass
class Analise:
    empresa: dict
    mes: str                     # mês de referência (o último completo)
    kpis: dict
    evolucao: pd.DataFrame
    clientes: pd.DataFrame
    risco: pd.DataFrame
    quedas: pd.DataFrame
    subidas: pd.DataFrame
    novos: pd.DataFrame
    categorias: pd.DataFrame
    preco_volume: pd.DataFrame
    produtos: pd.DataFrame
    devolucoes: pd.DataFrame
    concentracao: dict
    achados: list = field(default_factory=list)


MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
            "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _euros(v: float) -> str:
    return f"{v:,.0f} €".replace(",", " ")


def mes_extenso(mes: str) -> str:
    """'2026-08' -> 'agosto de 2026'."""
    p = pd.Period(mes, freq="M")
    return f"{MESES_PT[p.month - 1]} de {p.year}"


def _pct(v: float) -> str:
    """Percentagem com uma casa decimal quando é pequena, senão inteira."""
    texto = f"{v:.1%}" if abs(v) < 0.10 else f"{v:.0%}"
    return texto.replace(".", ",").replace("%", "\u00a0%")


def _variacao(novo: float, velho: float) -> float | None:
    if velho == 0:
        return None
    return (novo - velho) / abs(velho)


def _meses_antes(mes: str, n: int) -> str:
    return str(pd.Period(mes, freq="M") - n)


def analisar(dados: Dados, mes_ref: str | None = None) -> Analise:
    docs = dados.documentos.copy()
    linhas = dados.linhas.copy()

    meses = sorted(docs["mes"].unique())
    mes = mes_ref or meses[-1]
    if mes not in meses:
        raise ValueError(f"O mês {mes} não existe nos dados (há {meses[0]} a {meses[-1]}).")

    evolucao = _evolucao(docs)
    kpis = _kpis(docs, evolucao, mes)
    clientes = _clientes(docs, mes)
    risco = _risco(clientes)
    quedas, subidas, novos = _movimentos(docs, mes)
    categorias = _categorias(linhas, mes)
    preco_volume = _preco_volume(linhas, mes)
    produtos = _produtos(linhas, mes)
    devolucoes = _devolucoes(docs, linhas, mes)
    concentracao = _concentracao(clientes)

    analise = Analise(
        empresa=dados.empresa, mes=mes, kpis=kpis, evolucao=evolucao, clientes=clientes,
        risco=risco, quedas=quedas, subidas=subidas, novos=novos, categorias=categorias,
        preco_volume=preco_volume, produtos=produtos, devolucoes=devolucoes,
        concentracao=concentracao,
    )
    analise.achados = _achados(analise)
    return analise


# --------------------------------------------------------------------------- KPIs

def _evolucao(docs: pd.DataFrame) -> pd.DataFrame:
    ev = docs.groupby("mes").agg(
        faturacao=("liquido", "sum"),
        encomendas=("documento", "nunique"),
        clientes=("cliente_id", "nunique"),
    ).reset_index()
    ev["ticket_medio"] = ev["faturacao"] / ev["encomendas"]
    ev["media_3m"] = ev["faturacao"].rolling(3, min_periods=1).mean()
    ev["homologo"] = ev["faturacao"].shift(12)
    ev["var_homologa"] = (ev["faturacao"] - ev["homologo"]) / ev["homologo"]
    return ev


def _kpis(docs: pd.DataFrame, ev: pd.DataFrame, mes: str) -> dict:
    linha = ev[ev["mes"] == mes].iloc[0]
    anterior = ev[ev["mes"] == _meses_antes(mes, 1)]
    homologo = ev[ev["mes"] == _meses_antes(mes, 12)]

    dm = docs[docs["mes"] == mes]
    devolucoes = -dm.loc[dm["liquido"] < 0, "liquido"].sum()
    vendas_brutas = dm.loc[dm["liquido"] > 0, "liquido"].sum()

    ultimos12 = [str(pd.Period(mes, freq="M") - i) for i in range(12)]
    doze = docs[docs["mes"].isin(ultimos12)]
    anteriores12 = [str(pd.Period(mes, freq="M") - i) for i in range(12, 24)]
    doze_antes = docs[docs["mes"].isin(anteriores12)]

    def antes(coluna):
        return float(anterior[coluna].iloc[0]) if len(anterior) else None

    def homo(coluna):
        return float(homologo[coluna].iloc[0]) if len(homologo) else None

    return {
        "faturacao": float(linha["faturacao"]),
        "faturacao_mes_anterior": antes("faturacao"),
        "faturacao_homologa": homo("faturacao"),
        "var_mensal": _variacao(linha["faturacao"], antes("faturacao") or 0),
        "var_homologa": _variacao(linha["faturacao"], homo("faturacao") or 0),
        "encomendas": int(linha["encomendas"]),
        "encomendas_homologa": homo("encomendas"),
        "clientes_ativos": int(linha["clientes"]),
        "clientes_homologa": homo("clientes"),
        "ticket_medio": float(linha["ticket_medio"]),
        "ticket_homologo": homo("ticket_medio"),
        "devolucoes": float(devolucoes),
        "peso_devolucoes": float(devolucoes / vendas_brutas) if vendas_brutas else 0.0,
        "faturacao_12m": float(doze["liquido"].sum()),
        "faturacao_12m_anterior": float(doze_antes["liquido"].sum()) if len(doze_antes) else None,
        "meses_disponiveis": int(docs["mes"].nunique()),
    }


# ----------------------------------------------------------------- clientes/risco

def _clientes(docs: pd.DataFrame, mes: str) -> pd.DataFrame:
    fim = pd.Period(mes, freq="M").to_timestamp(how="end").normalize()
    doze = [str(pd.Period(mes, freq="M") - i) for i in range(12)]
    doze_antes = [str(pd.Period(mes, freq="M") - i) for i in range(12, 24)]

    base = docs.groupby(["cliente_id", "cliente_nome"]).agg(
        primeira_compra=("data", "min"),
        ultima_compra=("data", "max"),
        encomendas=("documento", "nunique"),
        total=("liquido", "sum"),
    ).reset_index()

    v12 = docs[docs["mes"].isin(doze)].groupby("cliente_id")["liquido"].sum()
    v12a = docs[docs["mes"].isin(doze_antes)].groupby("cliente_id")["liquido"].sum()
    m12 = docs[docs["mes"].isin(doze)].groupby("cliente_id")["mes"].nunique()

    base["valor_12m"] = base["cliente_id"].map(v12).fillna(0.0)
    base["valor_12m_anterior"] = base["cliente_id"].map(v12a).fillna(0.0)
    base["meses_ativos_12m"] = base["cliente_id"].map(m12).fillna(0).astype(int)
    base["var_12m"] = np.where(
        base["valor_12m_anterior"] > 0,
        (base["valor_12m"] - base["valor_12m_anterior"]) / base["valor_12m_anterior"],
        np.nan,
    )
    base["dias_sem_comprar"] = (fim - base["ultima_compra"]).dt.days

    # intervalo típico entre encomendas (mediana), por cliente
    datas = docs.sort_values("data").groupby("cliente_id")["data"]
    intervalos = datas.apply(lambda s: s.drop_duplicates().diff().dt.days.median())
    base["intervalo_tipico"] = base["cliente_id"].map(intervalos)
    base["intervalo_tipico"] = base["intervalo_tipico"].fillna(60).clip(lower=7, upper=120)
    base["atraso"] = base["dias_sem_comprar"] / base["intervalo_tipico"]

    base["estado"] = "Ativo"
    base.loc[(base["atraso"] >= 1.5) & (base["dias_sem_comprar"] >= 21), "estado"] = "A abrandar"
    base.loc[(base["atraso"] >= 3.0) & (base["dias_sem_comprar"] >= 45), "estado"] = "Em risco"
    base.loc[(base["atraso"] >= 6.0) & (base["dias_sem_comprar"] >= 90), "estado"] = "Perdido"

    # Ritmo anual que o cliente tinha quando ainda comprava. Limitado ao melhor
    # ano que ele realmente fez, para não prometer números que nunca existiram.
    ritmo = np.maximum(base["meses_ativos_12m"], 1)
    estimado = base["valor_12m"] / ritmo * 12
    teto = np.maximum(base["valor_12m"], base["valor_12m_anterior"])
    base["valor_anual_estimado"] = np.where(
        base["dias_sem_comprar"] > 365, 0.0, np.minimum(estimado, teto))
    return base.sort_values("valor_12m", ascending=False).reset_index(drop=True)


def _risco(clientes: pd.DataFrame) -> pd.DataFrame:
    r = clientes[
        clientes["estado"].isin(["Em risco", "Perdido", "A abrandar"])
        & (clientes["valor_anual_estimado"] >= VALOR_MINIMO_ACAO)
        & (clientes["encomendas"] >= 3)
    ].copy()
    # ordena pelo dinheiro, não pelo estado: o que interessa é a quem ligar primeiro
    return r.sort_values("valor_anual_estimado", ascending=False).reset_index(drop=True)


def _movimentos(docs: pd.DataFrame, mes: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Quem caiu, quem subiu e quem é novo — últimos 3 meses vs homólogos."""
    p = pd.Period(mes, freq="M")
    atual = [str(p - i) for i in range(3)]
    homologo = [str(p - i) for i in range(12, 15)]

    a = docs[docs["mes"].isin(atual)].groupby(["cliente_id", "cliente_nome"])["liquido"].sum()
    h = docs[docs["mes"].isin(homologo)].groupby(["cliente_id", "cliente_nome"])["liquido"].sum()
    comp = pd.concat([a.rename("atual"), h.rename("homologo")], axis=1).fillna(0.0).reset_index()
    comp["diferenca"] = comp["atual"] - comp["homologo"]
    comp["variacao"] = np.where(comp["homologo"] > 0,
                                comp["diferenca"] / comp["homologo"], np.nan)

    quedas = comp[(comp["homologo"] > 0) & (comp["diferenca"] < -150)] \
        .sort_values("diferenca").reset_index(drop=True)
    subidas = comp[(comp["homologo"] > 0) & (comp["diferenca"] > 150)] \
        .sort_values("diferenca", ascending=False).reset_index(drop=True)

    primeira = docs.groupby("cliente_id")["data"].min()
    limite = (p - 11).to_timestamp()
    ids_novos = primeira[primeira >= limite].index
    novos = docs[docs["cliente_id"].isin(ids_novos)] \
        .groupby(["cliente_id", "cliente_nome"]).agg(
            primeira_compra=("data", "min"), total=("liquido", "sum")) \
        .reset_index().sort_values("total", ascending=False).reset_index(drop=True)
    return quedas, subidas, novos


# ----------------------------------------------------------- categorias/ produtos

def _janelas(mes: str) -> tuple[list[str], list[str]]:
    p = pd.Period(mes, freq="M")
    return [str(p - i) for i in range(12)], [str(p - i) for i in range(12, 24)]


def _categorias(linhas: pd.DataFrame, mes: str) -> pd.DataFrame:
    atual, anterior = _janelas(mes)
    a = linhas[linhas["mes"].isin(atual)].groupby("categoria")["liquido"].sum()
    b = linhas[linhas["mes"].isin(anterior)].groupby("categoria")["liquido"].sum()
    cat = pd.concat([a.rename("ultimos_12m"), b.rename("anteriores_12m")], axis=1).fillna(0.0)
    cat = cat.reset_index()
    cat["diferenca"] = cat["ultimos_12m"] - cat["anteriores_12m"]
    cat["variacao"] = np.where(cat["anteriores_12m"] > 0,
                               cat["diferenca"] / cat["anteriores_12m"], np.nan)
    total = cat["ultimos_12m"].sum()
    cat["peso"] = cat["ultimos_12m"] / total if total else 0.0
    return cat.sort_values("ultimos_12m", ascending=False).reset_index(drop=True)


def _preco_volume(linhas: pd.DataFrame, mes: str) -> pd.DataFrame:
    """Separa a variação da faturação em efeito preço, efeito volume e gama.

    Para cada produto vendido nos dois períodos:
        efeito volume = preço antigo x (quantidade nova - quantidade antiga)
        efeito preço  = quantidade antiga x (preço novo - preço antigo)
        efeito misto  = (variação de preço) x (variação de quantidade)
    Produtos que só existem num dos períodos entram em "gama".
    """
    atual, anterior = _janelas(mes)
    vendas = linhas[linhas["liquido"] > 0]

    def agregar(meses):
        g = vendas[vendas["mes"].isin(meses)].groupby(["categoria", "produto_id"]).agg(
            valor=("liquido", "sum"), qtd=("quantidade", "sum")).reset_index()
        g["preco"] = np.where(g["qtd"] > 0, g["valor"] / g["qtd"], np.nan)
        return g

    a, b = agregar(atual), agregar(anterior)
    j = a.merge(b, on=["categoria", "produto_id"], how="outer", suffixes=("_novo", "_velho"))
    j[["valor_novo", "valor_velho", "qtd_novo", "qtd_velho"]] = \
        j[["valor_novo", "valor_velho", "qtd_novo", "qtd_velho"]].fillna(0.0)

    comuns = j[(j["qtd_novo"] > 0) & (j["qtd_velho"] > 0)].copy()
    comuns["ef_volume"] = comuns["preco_velho"] * (comuns["qtd_novo"] - comuns["qtd_velho"])
    comuns["ef_preco"] = comuns["qtd_velho"] * (comuns["preco_novo"] - comuns["preco_velho"])
    comuns["ef_misto"] = (comuns["preco_novo"] - comuns["preco_velho"]) * \
                         (comuns["qtd_novo"] - comuns["qtd_velho"])
    so_novos = j[(j["qtd_velho"] == 0)].groupby("categoria")["valor_novo"].sum()
    so_velhos = j[(j["qtd_novo"] == 0)].groupby("categoria")["valor_velho"].sum()

    res = comuns.groupby("categoria")[["ef_volume", "ef_preco", "ef_misto"]].sum()
    res["ef_gama"] = so_novos.reindex(res.index).fillna(0.0) - \
        so_velhos.reindex(res.index).fillna(0.0)
    res["total_novo"] = j.groupby("categoria")["valor_novo"].sum().reindex(res.index).fillna(0.0)
    res["total_velho"] = j.groupby("categoria")["valor_velho"].sum().reindex(res.index).fillna(0.0)
    res["diferenca"] = res["total_novo"] - res["total_velho"]
    res["preco_medio_var"] = np.where(
        res["total_velho"] > 0, res["ef_preco"] / res["total_velho"], np.nan)
    return res.reset_index().sort_values("diferenca").reset_index(drop=True)


def _produtos(linhas: pd.DataFrame, mes: str) -> pd.DataFrame:
    atual, anterior = _janelas(mes)
    vendas = linhas[linhas["liquido"] > 0]
    nomes = vendas.groupby("produto_id")["produto_nome"].last()
    cats = vendas.groupby("produto_id")["categoria"].last()
    a = vendas[vendas["mes"].isin(atual)].groupby("produto_id")["liquido"].sum()
    b = vendas[vendas["mes"].isin(anterior)].groupby("produto_id")["liquido"].sum()
    p = pd.concat([a.rename("ultimos_12m"), b.rename("anteriores_12m")], axis=1).fillna(0.0)
    p["produto_nome"] = p.index.map(nomes)
    p["categoria"] = p.index.map(cats)
    p["diferenca"] = p["ultimos_12m"] - p["anteriores_12m"]
    return p.reset_index().sort_values("ultimos_12m", ascending=False).reset_index(drop=True)


def _devolucoes(docs: pd.DataFrame, linhas: pd.DataFrame, mes: str) -> pd.DataFrame:
    atual, _ = _janelas(mes)
    dev = linhas[(linhas["mes"].isin(atual)) & (linhas["liquido"] < 0)]
    if dev.empty:
        return pd.DataFrame(columns=["produto_nome", "categoria", "valor", "ocorrencias"])
    r = dev.groupby(["produto_nome", "categoria"]).agg(
        valor=("liquido", lambda s: -s.sum()),
        ocorrencias=("documento", "nunique")).reset_index()
    return r.sort_values("valor", ascending=False).reset_index(drop=True)


def _concentracao(clientes: pd.DataFrame) -> dict:
    v = clientes.loc[clientes["valor_12m"] > 0, "valor_12m"].sort_values(ascending=False)
    total = v.sum()
    if total <= 0 or v.empty:
        return {"total": 0.0, "n_clientes": 0}
    acumulado = v.cumsum() / total
    return {
        "total": float(total),
        "n_clientes": int(len(v)),
        "clientes_50pct": int((acumulado < 0.5).sum() + 1),
        "clientes_80pct": int((acumulado < 0.8).sum() + 1),
        "peso_top10": float(v.head(10).sum() / total),
        "peso_maior": float(v.iloc[0] / total),
    }


# ------------------------------------------------------------------------ achados

def _achados(a: Analise) -> list[dict]:
    """As conclusões que vão para o email, cada uma com uma ação concreta."""
    out: list[dict] = []
    k = a.kpis

    # 1. faturação do mês
    if k["var_homologa"] is not None:
        sinal = "subiu" if k["var_homologa"] >= 0 else "caiu"
        out.append({
            "tipo": "positivo" if k["var_homologa"] >= 0 else "alerta",
            "titulo": f"Faturação de {mes_extenso(a.mes)}: {_euros(k['faturacao'])}",
            "texto": (f"{sinal} {_pct(abs(k['var_homologa']))} face ao mesmo mês do ano passado "
                      f"({_euros(k['faturacao_homologa'])}). Nos últimos 12 meses somou "
                      f"{_euros(k['faturacao_12m'])}."),
            "acao": None,
        })

    # 2. clientes em risco — o dinheiro mais fácil de recuperar
    risco = a.risco[a.risco["estado"].isin(["Em risco", "Perdido"])]
    if len(risco):
        valor = risco["valor_anual_estimado"].sum()
        nomes = ", ".join(risco.head(3)["cliente_nome"])
        out.append({
            "tipo": "alerta",
            "titulo": f"{len(risco)} clientes deixaram de comprar — {_euros(valor)}/ano em risco",
            "texto": (f"Compravam com regularidade e estão há muito tempo sem encomendar. "
                      f"Os três maiores: {nomes}."),
            "acao": ("Ligar esta semana aos 10 primeiros da lista. Recuperar metade vale "
                     f"{_euros(valor * 0.5)} por ano."),
        })

    # 3. quedas em clientes que ainda compram
    if len(a.quedas):
        perda = -a.quedas["diferenca"].sum()
        top = a.quedas.head(3)
        detalhe = "; ".join(
            f"{r.cliente_nome} {_euros(-r.diferenca)}" for r in top.itertuples())
        out.append({
            "tipo": "alerta",
            "titulo": f"{len(a.quedas)} clientes a comprar menos — {_euros(perda)} no trimestre",
            "texto": (f"Comparação dos últimos 3 meses com os mesmos 3 meses do ano passado, "
                      f"para não confundir com a sazonalidade. Maiores quedas: {detalhe}."),
            "acao": "Visitar os 5 primeiros e perceber se foi preço, rutura ou concorrência.",
        })

    # 4. categorias
    if len(a.categorias):
        pior = a.categorias.sort_values("diferenca").iloc[0]
        melhor = a.categorias.sort_values("diferenca").iloc[-1]
        if pior["diferenca"] < 0:
            out.append({
                "tipo": "alerta",
                "titulo": f"{pior['categoria']}: {_pct(pior['variacao'])} em 12 meses",
                "texto": (f"Passou de {_euros(pior['anteriores_12m'])} para "
                          f"{_euros(pior['ultimos_12m'])}, menos "
                          f"{_euros(-pior['diferenca'])}. É {_pct(pior['peso'])} da faturação."),
                "acao": "Ver se é perda de clientes ou de quota dentro dos mesmos clientes.",
            })
        if melhor["diferenca"] > 0:
            out.append({
                "tipo": "positivo",
                "titulo": f"{melhor['categoria']}: +{_pct(melhor['variacao'])} em 12 meses",
                "texto": (f"Mais {_euros(melhor['diferenca'])} do que no período anterior. "
                          f"Já pesa {_pct(melhor['peso'])} da faturação."),
                "acao": "Oferecer esta categoria aos clientes que ainda não a compram.",
            })

    # 5. preço vs volume
    pv = a.preco_volume
    if len(pv):
        preco = pv["ef_preco"].sum()
        volume = pv["ef_volume"].sum()
        total = pv["diferenca"].sum()
        if abs(total) > 1 and preco > 0 and volume < 0:
            cresceu = total > 0
            out.append({
                "tipo": "alerta",
                "titulo": ("O crescimento vem do preço, não de vender mais" if cresceu
                           else "Está a vender menos quantidade e a segurar com preço"),
                "texto": (f"Nos últimos 12 meses a subida de preços trouxe {_euros(preco)}, "
                          f"mas a quebra de quantidades tirou {_euros(-volume)}. "
                          + ("Sem o aumento de preços, a faturação tinha caído."
                             if cresceu else
                             "O preço já não chega para compensar o volume perdido.")),
                "acao": "Confirmar se há clientes a comprar o mesmo produto a outro fornecedor.",
            })
        elif abs(total) > 1 and volume > 0:
            out.append({
                "tipo": "positivo",
                "titulo": "Crescimento com volume real",
                "texto": (f"Nos últimos 12 meses o volume trouxe {_euros(volume)} e o preço "
                          f"{_euros(preco)}. O crescimento não é só inflação."),
                "acao": None,
            })

    # 6. concentração
    c = a.concentracao
    if c.get("n_clientes"):
        out.append({
            "tipo": "alerta" if c["peso_top10"] > 0.5 else "info",
            "titulo": f"Os 10 maiores clientes são {_pct(c['peso_top10'])} da faturação",
            "texto": (f"{c['clientes_50pct']} clientes fazem metade das vendas e "
                      f"{c['clientes_80pct']} fazem 80%. O maior sozinho vale "
                      f"{_pct(c['peso_maior'])}."),
            "acao": ("Proteger estas contas com visitas regulares e reduzir a dependência."
                     if c["peso_top10"] > 0.5 else None),
        })

    # 7. devoluções
    if k["peso_devolucoes"] > 0.01 and len(a.devolucoes):
        pior = a.devolucoes.iloc[0]
        out.append({
            "tipo": "alerta",
            "titulo": f"Devoluções em {_pct(k['peso_devolucoes'])} das vendas do mês",
            "texto": (f"No último ano o produto com mais devoluções foi "
                      f"\"{pior['produto_nome']}\" ({_euros(pior['valor'])} em "
                      f"{int(pior['ocorrencias'])} notas de crédito)."),
            "acao": "Verificar transporte e prazos de validade nesse produto.",
        })

    # 8. novos clientes
    if len(a.novos):
        out.append({
            "tipo": "positivo",
            "titulo": f"{len(a.novos)} clientes novos em 12 meses",
            "texto": (f"Valem {_euros(a.novos['total'].sum())} desde a primeira compra. "
                      f"O maior é {a.novos.iloc[0]['cliente_nome']}."),
            "acao": "Confirmar se os novos do último trimestre já repetiram encomenda.",
        })

    return out
