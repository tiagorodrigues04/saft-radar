"""Constrói o painel HTML e o texto do Raio-X que segue por email."""
from __future__ import annotations

from datetime import date
from html import escape

import pandas as pd

from .analise import Analise, mes_extenso
from .estilo import CSS, FONTES, JS
from .graficos import barras_agrupadas, barras_divergentes, euros, linha_evolucao, milhares, pct

ICONES = {
    "alerta": ('<svg width="17" height="17" viewBox="0 0 16 16" aria-hidden="true">'
               '<path d="M8 1.6 15 14H1L8 1.6Z" fill="none" stroke="currentColor" '
               'stroke-width="1.5" stroke-linejoin="round"/>'
               '<path d="M8 6v3.4" stroke="currentColor" stroke-width="1.5" '
               'stroke-linecap="round"/><circle cx="8" cy="11.6" r="0.95" '
               'fill="currentColor"/></svg>'),
    "positivo": ('<svg width="17" height="17" viewBox="0 0 16 16" aria-hidden="true">'
                 '<circle cx="8" cy="8" r="6.6" fill="none" stroke="currentColor" '
                 'stroke-width="1.5"/><path d="m5.1 8.2 2 2 3.8-4.2" fill="none" '
                 'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
                 'stroke-linejoin="round"/></svg>'),
    "info": ('<svg width="17" height="17" viewBox="0 0 16 16" aria-hidden="true">'
             '<circle cx="8" cy="8" r="6.6" fill="none" stroke="currentColor" '
             'stroke-width="1.5"/><path d="M8 7.2v4" stroke="currentColor" '
             'stroke-width="1.6" stroke-linecap="round"/><circle cx="8" cy="4.8" '
             'r="0.95" fill="currentColor"/></svg>'),
}
ETIQUETAS = {"alerta": "A corrigir", "positivo": "A aproveitar", "info": "Contexto"}
CHIPS = {"Perdido": "perdido", "Em risco": "risco", "A abrandar": "abrandar"}


def _delta(valor: float | None, sufixo: str = "") -> str:
    if valor is None:
        return '<span class="nota">sem termo de comparação</span>'
    classe = "sobe" if valor >= 0 else "desce"
    seta = "▲" if valor >= 0 else "▼"
    return (f'<span class="delta {classe}">{seta} {pct(valor).lstrip("+")}</span>'
            f'<span class="nota"> {sufixo}</span>')


def _kpi(nome: str, valor: str, nota: str) -> str:
    return (f'<div class="kpi"><div class="nome">{nome}</div>'
            f'<div class="valor">{valor}</div><div class="nota">{nota}</div></div>')


def _tabela(cabecalhos: list[str], linhas: list[list[str]], alinhar_dir: set[int]) -> str:
    ths = "".join(f'<th class="{"num" if i in alinhar_dir else ""}">{escape(h)}</th>'
                  for i, h in enumerate(cabecalhos))
    corpo = []
    for linha in linhas:
        tds = "".join(f'<td class="{"num" if i in alinhar_dir else ""}">{c}</td>'
                      for i, c in enumerate(linha))
        corpo.append(f"<tr>{tds}</tr>")
    return (f'<div class="rolar"><table><thead><tr>{ths}</tr></thead>'
            f'<tbody>{"".join(corpo)}</tbody></table></div>')


def gerar_html(a: Analise, limite_risco: int = 12) -> str:
    k = a.kpis
    empresa = escape(a.empresa.get("nome", "Empresa"))
    p = []

    p.append(f"<title>Raio-X {escape(a.empresa.get('nome', 'Vendas').split(',')[0])}</title>")
    p.append(FONTES)
    p.append(f"<style>{CSS}</style>")
    p.append('<div class="folha">')

    # ------------------------------------------------------------- cabeçalho
    p.append('<header class="masthead">')
    p.append('<div class="sobrescrito">Raio-X mensal de vendas</div>')
    p.append(f"<h1>{empresa}</h1>")
    p.append('<div class="identificacao">'
             f'<span>Mês em análise <b>{mes_extenso(a.mes)}</b></span>'
             f'<span>NIF <b>{escape(a.empresa.get("nif", "—"))}</b></span>'
             f'<span>Base <b>SAF-T {escape(a.empresa.get("versao", "PT"))}</b>, '
             f'{k["meses_disponiveis"]} meses</span>'
             f'<span>Emitido a <b>{date.today().strftime("%d/%m/%Y")}</b></span>'
             "</div>")
    p.append('<div class="selo">'
             '<svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true">'
             '<circle cx="8" cy="8" r="6.6" fill="none" stroke="currentColor" '
             'stroke-width="1.4"/><path d="m5.1 8.2 2 2 3.8-4.2" fill="none" '
             'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
             'stroke-linejoin="round"/></svg>'
             "Totais conferidos com o cabeçalho de cada ficheiro SAF-T. "
             "Documentos anulados excluídos; notas de crédito abatidas.</div>")
    p.append("</header>")

    # ------------------------------------------------------------------ KPIs
    p.append('<div class="kpis">')
    p.append(_kpi("Faturação do mês", euros(k["faturacao"]),
                  _delta(k["var_homologa"], "vs. ano anterior")))
    p.append(_kpi("Últimos 12 meses", euros(k["faturacao_12m"]),
                  _delta(None if not k["faturacao_12m_anterior"] else
                         (k["faturacao_12m"] - k["faturacao_12m_anterior"]) /
                         k["faturacao_12m_anterior"], "vs. 12 meses anteriores")))
    p.append(_kpi("Clientes que compraram", milhares(k["clientes_ativos"]),
                  _delta(None if not k["clientes_homologa"] else
                         (k["clientes_ativos"] - k["clientes_homologa"]) /
                         k["clientes_homologa"], "vs. ano anterior")))
    p.append(_kpi("Valor por encomenda", euros(k["ticket_medio"]),
                  f'{milhares(k["encomendas"])} encomendas no mês'))
    p.append(_kpi("Devoluções", euros(k["devolucoes"]),
                  f'{pct(k["peso_devolucoes"]).lstrip("+")} das vendas do mês'))
    p.append("</div>")

    # --------------------------------------------------------------- achados
    p.append("<section>")
    p.append('<div class="titulo-seccao"><h2>O que fazer este mês</h2>'
             '<span class="contexto">Por ordem de dinheiro em jogo</span></div>')
    p.append('<div class="achados">')
    for ach in a.achados:
        tipo = ach["tipo"]
        acao = (f'<div class="acao"><b>Ação:</b> {escape(ach["acao"])}</div>'
                if ach.get("acao") else "")
        p.append(f'<article class="achado {tipo}">'
                 f'<span class="icone">{ICONES[tipo]}</span>'
                 f'<div class="conteudo">'
                 f'<div class="etiqueta">{ETIQUETAS[tipo]}</div>'
                 f'<h3>{escape(ach["titulo"])}</h3>'
                 f'<div class="corpo">{escape(ach["texto"])}</div>{acao}'
                 f'</div></article>')
    p.append("</div></section>")

    # -------------------------------------------------------------- evolução
    ev = a.evolucao
    p.append("<section>")
    p.append('<div class="titulo-seccao"><h2>Evolução mensal</h2>'
             '<span class="contexto">Faturação líquida de IVA, sem documentos anulados'
             "</span></div>")
    p.append('<div class="cartao enchido">')
    p.append('<div class="moldura-grafico">' + linha_evolucao(list(ev["mes"]), list(ev["faturacao"]), list(ev["media_3m"])) + "</div>")
    p.append('<div class="legenda">'
             '<span><i class="marca s1"></i>Faturação do mês</span>'
             '<span><i class="marca tracejado"></i>Média dos últimos 3 meses</span></div>')
    linhas_ev = [[mes_extenso(r.mes).capitalize(), euros(r.faturacao),
                  milhares(r.encomendas), milhares(r.clientes), euros(r.ticket_medio),
                  pct(r.var_homologa) if pd.notna(r.var_homologa) else "—"]
                 for r in ev.itertuples()]
    p.append('<details><summary>Ver os números mês a mês</summary>'
             + _tabela(["Mês", "Faturação", "Encomendas", "Clientes", "Por encomenda",
                        "vs. ano anterior"], linhas_ev, {1, 2, 3, 4, 5}) + "</details>")
    p.append("</div></section>")

    # ------------------------------------------------------------ categorias
    cat = a.categorias
    p.append("<section>")
    p.append('<div class="titulo-seccao"><h2>Onde ganhou e onde perdeu</h2>'
             '<span class="contexto">Últimos 12 meses vs. os 12 anteriores</span></div>')
    p.append('<div class="cartao enchido">')
    extras = [f"||Últimos 12 meses|{euros(r.ultimos_12m)}||12 meses antes|"
              f"{euros(r.anteriores_12m)}" for r in cat.itertuples()]
    p.append('<div class="moldura-grafico">' + barras_divergentes(list(cat["categoria"]), list(cat["diferenca"]), extras) + "</div>")
    p.append('<div class="legenda">'
             '<span><i class="marca s1"></i>Cresceu</span>'
             '<span><i class="marca critico"></i>Caiu</span></div>')
    linhas_cat = [[escape(r.categoria), euros(r.ultimos_12m), euros(r.anteriores_12m),
                   euros(r.diferenca), pct(r.variacao), pct(r.peso).lstrip("+")]
                  for r in cat.itertuples()]
    p.append('<details><summary>Ver a tabela das categorias</summary>'
             + _tabela(["Categoria", "Últimos 12 meses", "12 meses antes", "Diferença",
                        "Variação", "Peso"], linhas_cat, {1, 2, 3, 4, 5}) + "</details>")
    p.append("</div></section>")

    # ---------------------------------------------------------- preço/volume
    pv = a.preco_volume
    p.append("<section>")
    p.append('<div class="titulo-seccao"><h2>Foi o preço ou foi a quantidade?</h2>'
             '<span class="contexto">Quanto da variação veio de cada um</span></div>')
    p.append('<div class="cartao enchido">')
    p.append('<div class="moldura-grafico">' + barras_agrupadas(
        list(pv["categoria"]), list(pv["ef_volume"]), list(pv["ef_preco"]),
        "Efeito da quantidade", "Efeito do preço") + "</div>")
    p.append('<div class="legenda">'
             '<span><i class="marca s1"></i>Quantidade vendida</span>'
             '<span><i class="marca s2"></i>Preço praticado</span></div>')
    linhas_pv = [[escape(r.categoria), euros(r.ef_volume), euros(r.ef_preco),
                  euros(r.ef_gama), euros(r.diferenca)] for r in pv.itertuples()]
    linhas_pv.append(["<b>Total</b>", f"<b>{euros(pv['ef_volume'].sum())}</b>",
                      f"<b>{euros(pv['ef_preco'].sum())}</b>",
                      f"<b>{euros(pv['ef_gama'].sum())}</b>",
                      f"<b>{euros(pv['diferenca'].sum())}</b>"])
    p.append('<details><summary>Ver a tabela e o que significa cada coluna</summary>'
             + _tabela(["Categoria", "Quantidade", "Preço", "Gama", "Variação total"],
                       linhas_pv, {1, 2, 3, 4})
             + '<p class="nota" style="margin-top:10px;color:var(--tinta2);'
               'font-size:.82rem">A coluna <b>Gama</b> é o efeito dos produtos que '
               "entraram ou saíram do catálogo e por isso não existem nos dois "
               "períodos. As quatro colunas somam a variação total.</p></details>")
    p.append("</div></section>")

    # ---------------------------------------------------------------- risco
    risco = a.risco.head(limite_risco)
    p.append("<section>")
    total_risco = a.risco["valor_anual_estimado"].sum()
    p.append('<div class="titulo-seccao"><h2>A quem ligar primeiro</h2>'
             f'<span class="contexto">{len(a.risco)} clientes, '
             f"{euros(total_risco)}/ano em jogo</span></div>")
    p.append('<div class="cartao">')
    linhas_risco = []
    for r in risco.itertuples():
        chip = CHIPS.get(r.estado, "")
        linhas_risco.append([
            f'<span class="nome-cliente">{escape(r.cliente_nome)}</span>',
            f'<span class="chip {chip}"><i class="bolha"></i>{escape(r.estado)}</span>',
            f"{int(r.dias_sem_comprar)} dias",
            f"{int(r.intervalo_tipico)} dias",
            euros(r.valor_12m),
            f"<b>{euros(r.valor_anual_estimado)}</b>",
        ])
    p.append(_tabela(["Cliente", "Estado", "Sem comprar há", "Costumava comprar de",
                      "Últimos 12 meses", "Valor anual em jogo"],
                     linhas_risco, {2, 3, 4, 5}))
    p.append("</div>")
    p.append('<p class="contexto" style="margin-top:9px;color:var(--tinta3);'
             'font-size:.8rem">O “valor anual em jogo” é o ritmo de compra que o '
             "cliente tinha enquanto comprava, limitado ao melhor ano que realmente "
             "fez. Não é uma previsão.</p>")
    p.append("</section>")

    # -------------------------------------------------------- quedas/subidas
    p.append("<section>")
    p.append('<div class="titulo-seccao"><h2>Quem mudou de comportamento</h2>'
             '<span class="contexto">Últimos 3 meses vs. os mesmos 3 meses do ano '
             "anterior</span></div>")
    p.append('<div class="duas lado-a-lado">')
    for titulo, tabela, sinal in (("Maiores quedas", a.quedas.head(8), -1),
                                  ("Maiores subidas", a.subidas.head(8), 1)):
        linhas = [[f'<span class="nome-cliente">{escape(r.cliente_nome)}</span>',
                   euros(r.atual), euros(r.homologo),
                   f'<b style="color:var(--{"critico" if sinal < 0 else "bom"}-tinta)">'
                   f"{euros(r.diferenca)}</b>"] for r in tabela.itertuples()]
        p.append(f'<div class="cartao"><div style="padding:14px 12px 0 12px">'
                 f"<h3>{titulo}</h3></div>"
                 + _tabela(["Cliente", "3 meses", "Ano anterior", "Diferença"],
                           linhas, {1, 2, 3}) + "</div>")
    p.append("</div></section>")

    # --------------------------------------------------------------- método
    c = a.concentracao
    p.append('<div class="metodo"><h3>Como estes números foram apurados</h3><ul>')
    p.append("<li>Fonte: ficheiros SAF-T de faturação exportados do programa "
             f"certificado ({escape(a.empresa.get('programa', '—'))}). Nada foi "
             "escrito à mão.</li>")
    p.append("<li>Valores líquidos de IVA. Documentos anulados excluídos e notas de "
             "crédito abatidas às vendas.</li>")
    p.append("<li>As comparações são sempre com o mesmo período do ano anterior, para "
             "a sazonalidade não confundir a leitura.</li>")
    p.append("<li>Um cliente entra em risco quando o tempo sem comprar passa a ser "
             "várias vezes o intervalo que ele costumava ter entre encomendas.</li>")
    if c.get("n_clientes"):
        p.append(f"<li>Concentração: {c['clientes_50pct']} clientes fazem metade da "
                 f"faturação e {c['clientes_80pct']} fazem 80%, num total de "
                 f"{c['n_clientes']} clientes ativos.</li>")
    p.append("</ul>")
    p.append('<p class="assinatura">Raio-X de vendas · gerado a partir dos ficheiros '
             "SAF-T do mês</p></div>")

    p.append("</div>")
    p.append('<div id="balao" role="status" aria-live="polite"></div>')
    p.append(f"<script>{JS}</script>")
    return "\n".join(p)


def texto_raio_x(a: Analise) -> str:
    """Versão em texto, para colar no corpo de um email."""
    k = a.kpis
    linhas = [
        f"RAIO-X DE {mes_extenso(a.mes).upper()}",
        a.empresa.get("nome", ""),
        "",
        f"Faturação do mês: {euros(k['faturacao'])} "
        f"({pct(k['var_homologa'])} face ao mesmo mês do ano passado)",
        f"Últimos 12 meses: {euros(k['faturacao_12m'])}",
        f"Clientes que compraram: {k['clientes_ativos']} · "
        f"{k['encomendas']} encomendas · {euros(k['ticket_medio'])} por encomenda",
        "",
        "O QUE FAZER ESTE MÊS",
    ]
    for i, ach in enumerate(a.achados, start=1):
        linhas.append("")
        linhas.append(f"{i}. {ach['titulo']}")
        linhas.append(f"   {ach['texto']}")
        if ach.get("acao"):
            linhas.append(f"   Ação: {ach['acao']}")
    if len(a.risco):
        linhas += ["", "CLIENTES A CONTACTAR (os 10 primeiros)"]
        for r in a.risco.head(10).itertuples():
            linhas.append(f"   · {r.cliente_nome} — {r.estado.lower()}, "
                          f"{int(r.dias_sem_comprar)} dias sem comprar, "
                          f"{euros(r.valor_anual_estimado)}/ano")
    linhas += ["", "Valores líquidos de IVA, apurados a partir dos ficheiros SAF-T. "
                   "Documentos anulados excluídos."]
    return "\n".join(linhas)
