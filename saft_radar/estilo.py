"""CSS e JS do painel. Ficam à parte para o gerador de HTML não ficar ilegível."""

FONTES = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
          '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
          '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
          'family=Bitter:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700'
          '&display=swap">')

CSS = """
:root {
  --plano:       #eef0f4;
  --superficie:  #ffffff;
  --superficie2: #f7f8fa;
  --tinta:       #12161c;
  --tinta2:      #4d586a;
  --tinta3:      #7b8798;
  --fio:         #e0e4eb;
  --fio-forte:   #c7ced9;
  --serie-1:     #2a78d6;
  --serie-2:     #eb6834;
  --serie-1-tenue: rgba(42,120,214,.14);
  --bom:         #0ca30c;
  --aviso:       #fab219;
  --serio:       #ec835a;
  --critico:     #d03b3b;
  --bom-tinta:   #067006;
  --critico-tinta: #a92b2b;
  --sombra:      0 1px 2px rgba(18,22,28,.06), 0 8px 24px -16px rgba(18,22,28,.24);
  --raio:        10px;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --plano:       #0d1015;
    --superficie:  #171b22;
    --superficie2: #1d222b;
    --tinta:       #f2f4f7;
    --tinta2:      #aab5c3;
    --tinta3:      #7f8b9a;
    --fio:         #262c36;
    --fio-forte:   #3a4250;
    --serie-1:     #3987e5;
    --serie-2:     #d95926;
    --serie-1-tenue: rgba(57,135,229,.18);
    --bom-tinta:   #35c035;
    --critico-tinta: #e06a6a;
    --sombra:      0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.7);
  }
}
:root[data-theme="dark"] {
  --plano:       #0d1015;
  --superficie:  #171b22;
  --superficie2: #1d222b;
  --tinta:       #f2f4f7;
  --tinta2:      #aab5c3;
  --tinta3:      #7f8b9a;
  --fio:         #262c36;
  --fio-forte:   #3a4250;
  --serie-1:     #3987e5;
  --serie-2:     #d95926;
  --serie-1-tenue: rgba(57,135,229,.18);
  --bom-tinta:   #35c035;
  --critico-tinta: #e06a6a;
  --sombra:      0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.7);
}

* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--plano);
  color: var(--tinta);
  font-family: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 15px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
  font-variant-numeric: tabular-nums;
}
.folha { max-width: 1060px; margin: 0 auto; padding: 0 16px; padding-block: 28px 56px; }
h1, h2, h3 { font-family: Bitter, Georgia, "Times New Roman", serif; text-wrap: balance;
             margin: 0; font-weight: 600; letter-spacing: -.01em; }
h1 { font-size: clamp(1.6rem, 4.2vw, 2.15rem); line-height: 1.18; }
h2 { font-size: 1.16rem; }
h3 { font-size: 1rem; }
p { margin: 0; }
a { color: var(--serie-1); }

/* ---------------------------------------------------------------- cabeçalho */
.masthead { border-bottom: 2px solid var(--tinta); padding-bottom: 18px; margin-bottom: 26px; }
.sobrescrito { font-size: .72rem; font-weight: 600; letter-spacing: .13em;
               text-transform: uppercase; color: var(--serie-1); margin-bottom: 8px; }
.identificacao { display: flex; flex-wrap: wrap; gap: 6px 18px; margin-top: 12px;
                 font-size: .82rem; color: var(--tinta2); }
.identificacao b { color: var(--tinta); font-weight: 600; }
.selo { display: inline-flex; align-items: center; gap: 7px; margin-top: 14px;
        padding: 5px 11px; border: 1px solid var(--fio); border-radius: 999px;
        background: var(--superficie); font-size: .76rem; color: var(--tinta2); }
.selo svg { flex: none; }

/* -------------------------------------------------------------------- KPIs */
.kpis { display: grid; gap: 1px; background: var(--fio); border: 1px solid var(--fio);
        border-radius: var(--raio); overflow: hidden; margin-bottom: 34px;
        grid-template-columns: repeat(auto-fit, minmax(168px, 1fr)); }
.kpi { background: var(--superficie); padding: 15px 16px 16px; }
.kpi .nome { font-size: .73rem; font-weight: 600; letter-spacing: .07em;
             text-transform: uppercase; color: var(--tinta3); }
.kpi .valor { font-family: Bitter, Georgia, serif; font-size: 1.62rem; font-weight: 600;
              line-height: 1.15; margin-top: 7px; }
.kpi .nota { font-size: .79rem; color: var(--tinta2); margin-top: 3px; }
.delta { display: inline-flex; align-items: center; gap: 4px; font-weight: 600; }
.delta.sobe { color: var(--bom-tinta); }
.delta.desce { color: var(--critico-tinta); }

/* ----------------------------------------------------------------- secções */
section { margin-bottom: 34px; }
.titulo-seccao { display: flex; align-items: baseline; justify-content: space-between;
                 gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.titulo-seccao .contexto { font-size: .8rem; color: var(--tinta3); }
.cartao { background: var(--superficie); border: 1px solid var(--fio);
          border-radius: var(--raio); box-shadow: var(--sombra); }
.cartao.enchido { padding: 18px; }

/* ------------------------------------------------------------------ achados */
.achados { display: flex; flex-direction: column; gap: 10px; }
.achado { display: flex; align-items: flex-start; gap: 13px;
          background: var(--superficie); border: 1px solid var(--fio);
          border-left: 4px solid var(--fio-forte); border-radius: var(--raio);
          padding: 15px 17px; box-shadow: var(--sombra); }
.achado.alerta  { border-left-color: var(--critico); }
.achado.positivo{ border-left-color: var(--bom); }
.achado.info    { border-left-color: var(--serie-1); }
.achado .icone { flex: none; margin-top: 3px; }
.achado .conteudo { min-width: 0; flex: 1; }
.achado .etiqueta { font-size: .68rem; font-weight: 700; letter-spacing: .1em;
                    text-transform: uppercase; color: var(--tinta3); }
.achado.alerta .etiqueta { color: var(--critico-tinta); }
.achado.positivo .etiqueta { color: var(--bom-tinta); }
.achado h3 { margin: 2px 0 5px; }
.achado .corpo { color: var(--tinta2); font-size: .92rem; }
.achado .acao { margin-top: 9px; padding-top: 9px; border-top: 1px dashed var(--fio);
                font-size: .89rem; }
.achado .acao b { font-weight: 600; }

/* ------------------------------------------------------------------ tabelas */
.rolar { overflow-x: auto; max-width: 100%; }
.cartao, .duas > * { min-width: 0; }
table { border-collapse: collapse; width: 100%; font-size: .88rem; }
th { text-align: left; font-weight: 600; font-size: .72rem; letter-spacing: .07em;
     text-transform: uppercase; color: var(--tinta3); padding: 9px 12px;
     border-bottom: 1px solid var(--fio-forte); white-space: nowrap; }
td { padding: 9px 12px; border-bottom: 1px solid var(--fio); vertical-align: middle; }
tr:last-child td { border-bottom: none; }
tbody tr:hover { background: var(--superficie2); }
.num { text-align: right; white-space: nowrap; }
.nome-cliente { font-weight: 500; }
.chip { display: inline-flex; align-items: center; gap: 5px; padding: 2px 8px;
        border-radius: 999px; font-size: .74rem; font-weight: 600; white-space: nowrap;
        border: 1px solid var(--fio-forte); color: var(--tinta2); }
.chip.perdido { border-color: var(--critico); color: var(--critico-tinta); }
.chip.risco { border-color: var(--serio); color: var(--tinta); }
.chip.abrandar { border-color: var(--aviso); color: var(--tinta); }
.chip .bolha { width: 7px; height: 7px; border-radius: 50%; flex: none; }
.chip.perdido .bolha { background: var(--critico); }
.chip.risco .bolha { background: var(--serio); }
.chip.abrandar .bolha { background: var(--aviso); }

/* ------------------------------------------------------------------ gráficos */
.moldura-grafico { overflow-x: auto; overflow-y: hidden; margin: 0 -4px; padding: 0 4px; }
.grafico { width: 100%; height: auto; display: block; min-width: 520px; }
.grelha { stroke: var(--fio); stroke-width: 1; }
.base { stroke: var(--fio-forte); stroke-width: 1; }
.eixo { fill: var(--tinta3); font-size: 11px; font-family: inherit; }
.eixo.fraco { fill: var(--tinta3); opacity: .75; font-size: 10px; }
.meio { text-anchor: middle; }
.fim { text-anchor: end; }
.inicio { text-anchor: start; }
.fim-dir { text-anchor: end; }
.rotulo { fill: var(--tinta); font-size: 12px; font-weight: 600; font-family: inherit; }
.rotulo.fraco { fill: var(--tinta2); font-weight: 500; }
.linha { fill: none; stroke-linejoin: round; stroke-linecap: round; }
.linha.principal { stroke: var(--serie-1); stroke-width: 2; }
.linha.media { stroke: var(--tinta3); stroke-width: 2; stroke-dasharray: 5 4; }
.area { fill: var(--serie-1-tenue); stroke: none; }
.ponto-fim { fill: var(--serie-1); stroke: var(--superficie); stroke-width: 2; }
.barra.sobe { fill: var(--serie-1); }
.barra.desce { fill: var(--critico); }
.barra.serie-1 { fill: var(--serie-1); }
.barra.serie-2 { fill: var(--serie-2); }
.alvo { cursor: pointer; }
rect.alvo:not(.barra) { fill: transparent; }
rect.alvo:hover { opacity: .82; }
.rotulo.dentro { fill: #fff; }
.legenda { display: flex; flex-wrap: wrap; gap: 8px 18px; margin-top: 10px;
           font-size: .8rem; color: var(--tinta2); }
.legenda span { display: inline-flex; align-items: center; gap: 7px; }
.marca { width: 13px; height: 3px; border-radius: 2px; flex: none; }
.marca.s1 { background: var(--serie-1); }
.marca.s2 { background: var(--serie-2); }
.marca.critico { background: var(--critico); }
.marca.tracejado { background: repeating-linear-gradient(90deg,
                   var(--tinta3) 0 5px, transparent 5px 9px); }

details { margin-top: 12px; }
summary { cursor: pointer; font-size: .82rem; color: var(--tinta2); width: fit-content; }
summary:focus-visible { outline: 2px solid var(--serie-1); outline-offset: 3px; }

/* --------------------------------------------------------------------- balão */
#balao { position: fixed; z-index: 40; pointer-events: none; opacity: 0;
         transition: opacity .12s; background: var(--superficie);
         border: 1px solid var(--fio-forte); border-radius: 8px; padding: 8px 11px;
         box-shadow: 0 8px 28px -10px rgba(0,0,0,.45); font-size: .82rem;
         min-width: 132px; }
#balao .cabeca { font-weight: 700; margin-bottom: 4px; }
#balao .par { display: flex; justify-content: space-between; gap: 16px;
              color: var(--tinta2); }
#balao .par b { color: var(--tinta); font-weight: 600; }

.duas { display: grid; gap: 18px; grid-template-columns: 1fr; }
@media (min-width: 880px) { .duas.lado-a-lado { grid-template-columns: 1fr 1fr; } }

.metodo { font-size: .82rem; color: var(--tinta2); border-top: 1px solid var(--fio);
          padding-top: 18px; margin-top: 42px; }
.metodo h3 { font-size: .9rem; margin-bottom: 7px; color: var(--tinta); }
.metodo ul { margin: 0; padding-left: 18px; }
.metodo li { margin-bottom: 4px; }
.assinatura { margin-top: 18px; font-size: .8rem; color: var(--tinta3); }

@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
@media print {
  body { background: #fff; }
  .cartao, .achado { box-shadow: none; break-inside: avoid; }
  #balao { display: none; }
}
"""

JS = """
(function () {
  var balao = document.getElementById('balao');
  if (!balao) return;
  function mostrar(e) {
    var alvo = e.target.closest('[data-titulo]');
    if (!alvo) return;
    var html = '<div class="cabeca">' + alvo.dataset.titulo + '</div>';
    (alvo.dataset.linhas || '').split('||').forEach(function (par) {
      if (!par) return;
      var p = par.split('|');
      html += '<div class="par"><span>' + p[0] + '</span><b>' + (p[1] || '') + '</b></div>';
    });
    balao.innerHTML = html;
    balao.style.opacity = '1';
    posicionar(e);
  }
  function posicionar(e) {
    var r = balao.getBoundingClientRect();
    var x = e.clientX + 14, y = e.clientY + 14;
    if (x + r.width > window.innerWidth - 8) x = e.clientX - r.width - 14;
    if (y + r.height > window.innerHeight - 8) y = e.clientY - r.height - 14;
    balao.style.left = Math.max(8, x) + 'px';
    balao.style.top = Math.max(8, y) + 'px';
  }
  document.addEventListener('pointerover', mostrar);
  document.addEventListener('pointermove', function (e) {
    if (balao.style.opacity === '1' && e.target.closest('[data-titulo]')) posicionar(e);
  });
  document.addEventListener('pointerout', function (e) {
    if (!e.relatedTarget || !e.relatedTarget.closest('[data-titulo]')) {
      balao.style.opacity = '0';
    }
  });
})();
"""
