"""Gráficos em SVG, escritos à mão para o painel não depender de nada externo."""
from __future__ import annotations

from html import escape


def euros(v: float, casas: int = 0) -> str:
    texto = f"{v:,.{casas}f}"
    inteiro, _, decimal = texto.partition(".")
    inteiro = inteiro.replace(",", " ")
    return f"{inteiro},{decimal} €" if decimal else f"{inteiro} €"


def milhares(v: float, casas: int = 0) -> str:
    texto = f"{v:,.{casas}f}"
    inteiro, _, decimal = texto.partition(".")
    inteiro = inteiro.replace(",", " ")
    return f"{inteiro},{decimal}" if decimal else inteiro


def pct(v: float | None, casas: int = 1) -> str:
    if v is None:
        return "—"
    return f"{v * 100:+.{casas}f} %".replace(".", ",")


MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun",
                "jul", "ago", "set", "out", "nov", "dez"]


def rotulo_mes(mes: str, com_ano: bool = False) -> str:
    ano, m = mes.split("-")
    curto = MESES_CURTOS[int(m) - 1]
    return f"{curto} {ano[2:]}" if com_ano else curto


def _escala(valor, vmin, vmax, pmin, pmax):
    if vmax == vmin:
        return (pmin + pmax) / 2
    return pmin + (valor - vmin) / (vmax - vmin) * (pmax - pmin)


def _passo(intervalo: float, alvo: int = 4) -> float:
    if intervalo <= 0:
        return 1.0
    bruto = intervalo / alvo
    import math
    magnitude = 10 ** math.floor(math.log10(bruto))
    for m in (1, 2, 2.5, 5, 10):
        if bruto <= magnitude * m:
            return magnitude * m
    return magnitude * 10


def linha_evolucao(meses: list[str], valores: list[float], media: list[float]) -> str:
    """Faturação mensal com média móvel de 3 meses. Cruz e balão ao passar o rato."""
    L, R, T, B = 62, 16, 26, 42
    W, H = 900, 330
    x0, x1 = L, W - R
    y0, y1 = T, H - B

    # A área preenchida obriga a escala a começar no zero: com um mínimo
    # recortado, o tamanho da mancha sugeria diferenças que não existem.
    vmax = max(max(valores), max(media)) * 1.10
    vmin = 0.0
    passo = _passo(vmax - vmin)
    base = 0.0
    linhas_y, t = [], base
    while t <= vmax:
        if t >= vmin:
            linhas_y.append(t)
        t += passo

    n = len(meses)
    px = [_escala(i, 0, max(n - 1, 1), x0, x1) for i in range(n)]
    py = [_escala(v, vmin, vmax, y1, y0) for v in valores]
    pm = [_escala(v, vmin, vmax, y1, y0) for v in media]

    partes = [f'<svg viewBox="0 0 {W} {H}" class="grafico" role="img" '
              f'aria-label="Faturação mensal dos últimos {n} meses">']
    for t in linhas_y:
        y = _escala(t, vmin, vmax, y1, y0)
        partes.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" class="grelha"/>')
        partes.append(f'<text x="{x0 - 10:.0f}" y="{y + 4:.1f}" class="eixo fim">'
                      f'{milhares(t / 1000)}k</text>')
    partes.append(f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" class="base"/>')

    for i, m in enumerate(meses):
        if i % 3 == 0 or i == n - 1:
            partes.append(f'<text x="{px[i]:.1f}" y="{y1 + 20:.0f}" class="eixo meio">'
                          f'{rotulo_mes(m)}</text>')
            if i == 0 or m.endswith("-01"):
                partes.append(f'<text x="{px[i]:.1f}" y="{y1 + 34:.0f}" class="eixo meio fraco">'
                              f'{m[:4]}</text>')

    area = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(px, py))
    partes.append(f'<polygon points="{px[0]:.1f},{y1} {area} {px[-1]:.1f},{y1}" class="area"/>')
    partes.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in zip(px, pm))}" '
                  f'class="linha media"/>')
    partes.append(f'<polyline points="{area}" class="linha principal"/>')

    ultimo = n - 1
    partes.append(f'<circle cx="{px[ultimo]:.1f}" cy="{py[ultimo]:.1f}" r="5" class="ponto-fim"/>')
    partes.append(f'<text x="{px[ultimo]:.1f}" y="{py[ultimo] - 14:.1f}" class="rotulo fim-dir">'
                  f'{milhares(valores[ultimo] / 1000, 1)}k €</text>')

    for i, m in enumerate(meses):
        partes.append(
            f'<rect x="{px[i] - 14:.1f}" y="{y0}" width="28" height="{y1 - y0}" '
            f'class="alvo" data-titulo="{rotulo_mes(m, True)}" '
            f'data-linhas="Faturação|{euros(valores[i])}||Média 3 meses|{euros(media[i])}"/>')
    partes.append("</svg>")
    return "".join(partes)


def barras_divergentes(rotulos: list[str], valores: list[float],
                       extras: list[str] | None = None) -> str:
    """Variação em euros por categoria: sobe para um lado, desce para o outro."""
    n = len(rotulos)
    altura_barra, espaco = 30, 16
    L, R, T, B = 178, 20, 10, 30
    H = T + n * altura_barra + (n - 1) * espaco + B
    W = 900
    x0, x1 = L, W - R

    limite = max(abs(min(valores)), abs(max(valores))) * 1.25 or 1
    zero = _escala(0, -limite, limite, x0, x1)

    partes = [f'<svg viewBox="0 0 {W} {H}" class="grafico" role="img" '
              f'aria-label="Variação da faturação por categoria em 12 meses">']
    passo = _passo(limite * 2, 4)
    t = -limite
    marcas = []
    k = 0
    while k * passo <= limite:
        marcas.extend([k * passo, -k * passo])
        k += 1
    for t in sorted(set(marcas)):
        if abs(t) > limite:
            continue
        x = _escala(t, -limite, limite, x0, x1)
        classe = "base" if t == 0 else "grelha"
        partes.append(f'<line x1="{x:.1f}" y1="{T}" x2="{x:.1f}" y2="{H - B}" class="{classe}"/>')
        partes.append(f'<text x="{x:.1f}" y="{H - B + 20}" class="eixo meio">'
                      f'{"0" if t == 0 else milhares(t / 1000) + "k"}</text>')

    for i, (rot, val) in enumerate(zip(rotulos, valores)):
        y = T + i * (altura_barra + espaco)
        x = _escala(val, -limite, limite, x0, x1)
        esq, larg = (min(zero, x), abs(x - zero))
        classe = "sobe" if val >= 0 else "desce"
        extra = extras[i] if extras else ""
        partes.append(
            f'<rect x="{esq:.1f}" y="{y}" width="{max(larg, 2):.1f}" height="{altura_barra}" '
            f'rx="4" class="barra {classe} alvo" data-titulo="{escape(rot)}" '
            f'data-linhas="Variação|{euros(val)}{extra}"/>')
        partes.append(f'<text x="{L - 12}" y="{y + altura_barra / 2 + 4:.0f}" '
                      f'class="rotulo fim">{escape(rot)}</text>')
        dentro = larg > 96
        if dentro:
            tx = x + (-8 if val >= 0 else 8)
            anchor = "fim" if val >= 0 else "inicio"
        else:
            tx = x + (8 if val >= 0 else -8)
            anchor = "inicio" if val >= 0 else "fim"
        classes = f'rotulo {anchor}' + (" dentro" if dentro else "")
        partes.append(f'<text x="{tx:.1f}" y="{y + altura_barra / 2 + 4:.0f}" '
                      f'class="{classes}">{euros(val)}</text>')
    partes.append("</svg>")
    return "".join(partes)


def barras_agrupadas(rotulos: list[str], serie_a: list[float], serie_b: list[float],
                     nome_a: str, nome_b: str) -> str:
    """Duas séries lado a lado (efeito volume vs efeito preço)."""
    n = len(rotulos)
    altura_barra, espaco_par, espaco_grupo = 15, 2, 22
    L, R, T, B = 178, 20, 10, 30
    altura_grupo = altura_barra * 2 + espaco_par
    H = T + n * altura_grupo + (n - 1) * espaco_grupo + B
    W = 900
    x0, x1 = L, W - R

    todos = serie_a + serie_b
    limite = max(abs(min(todos)), abs(max(todos))) * 1.45 or 1
    zero = _escala(0, -limite, limite, x0, x1)

    partes = [f'<svg viewBox="0 0 {W} {H}" class="grafico" role="img" '
              f'aria-label="Efeito do volume e do preço por categoria">']
    passo = _passo(limite * 2, 4)
    marcas, k = [], 0
    while k * passo <= limite:
        marcas.extend([k * passo, -k * passo])
        k += 1
    for t in sorted(set(marcas)):
        if abs(t) > limite:
            continue
        x = _escala(t, -limite, limite, x0, x1)
        partes.append(f'<line x1="{x:.1f}" y1="{T}" x2="{x:.1f}" y2="{H - B}" '
                      f'class="{"base" if t == 0 else "grelha"}"/>')
        partes.append(f'<text x="{x:.1f}" y="{H - B + 20}" class="eixo meio">'
                      f'{"0" if t == 0 else milhares(t / 1000) + "k"}</text>')

    for i, rot in enumerate(rotulos):
        topo = T + i * (altura_grupo + espaco_grupo)
        partes.append(f'<text x="{L - 12}" y="{topo + altura_grupo / 2 + 4:.0f}" '
                      f'class="rotulo fim">{escape(rot)}</text>')
        for j, (val, classe, nome) in enumerate(
                ((serie_a[i], "serie-1", nome_a), (serie_b[i], "serie-2", nome_b))):
            y = topo + j * (altura_barra + espaco_par)
            x = _escala(val, -limite, limite, x0, x1)
            esq, larg = min(zero, x), abs(x - zero)
            partes.append(
                f'<rect x="{esq:.1f}" y="{y}" width="{max(larg, 2):.1f}" '
                f'height="{altura_barra}" rx="3" class="barra {classe} alvo" '
                f'data-titulo="{escape(rot)}" data-linhas="{escape(nome)}|{euros(val)}"/>')
        maior = serie_a[i] if abs(serie_a[i]) >= abs(serie_b[i]) else serie_b[i]
        x = _escala(maior, -limite, limite, x0, x1)
        # Sempre por fora: o rótulo fica a meio do grupo, ou seja no vazio
        # entre as duas barras, onde texto claro sobre o fundo não se lê.
        tx = x + (8 if maior >= 0 else -8)
        anchor = "inicio" if maior >= 0 else "fim"
        partes.append(f'<text x="{tx:.1f}" y="{topo + altura_grupo / 2 + 4:.0f}" '
                      f'class="rotulo fraco {anchor}">{euros(maior)}</text>')
    partes.append("</svg>")
    return "".join(partes)
