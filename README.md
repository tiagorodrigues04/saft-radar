# Raio-X de vendas a partir de SAF-T

Pega nos ficheiros SAF-T de faturação de uma PME portuguesa e devolve um relatório
mensal com conclusões e ações concretas: que clientes estão a fugir, que categorias
estão a cair, e se a faturação está a crescer por vender mais ou só por cobrar mais caro.

O SAF-T (PT) é obrigatório em Portugal e qualquer programa de faturação certificado
o exporta. Tem lá dentro todas as vendas, linha a linha, com cliente, produto,
quantidade e preço — e a maior parte das empresas nunca olha para ele depois de o
entregar às Finanças.

**[Ver um relatório de exemplo](https://tiagorodrigues04.github.io/saft-radar/)**
(empresa fictícia, dados gerados)

---

## O problema

Um distribuidor com um milhão de euros de faturação tem os números todos no programa
de faturação e não consegue responder a perguntas simples:

- Que clientes compravam todos os meses e deixaram de comprar?
- A faturação subiu 4% — foi porque vendi mais ou porque os preços subiram?
- Que categoria está a perder terreno sem eu dar por isso?
- Quanto vale o cliente que estou prestes a perder?

Este projeto responde a essas perguntas a partir de ficheiros que a empresa já tem.

## O que faz

| Etapa | O que acontece |
|---|---|
| **Leitura** | Lê os SAF-T (`.xml`, `.xml.gz`, `.zip`), exclui documentos anulados, abate notas de crédito e confere os totais lidos com o cabeçalho de cada ficheiro |
| **Análise** | KPIs com comparação homóloga, deteção de clientes em risco, variação por categoria, decomposição preço/volume, concentração de clientes, devoluções |
| **Saída** | Painel HTML autónomo, texto pronto a colar num email, e CSV em modelo estrela para Power BI |

### Decisões de análise que fazem diferença

**Comparação homóloga, não com o mês anterior.** Numa distribuidora alimentar agosto
vale mais 40% do que fevereiro. Comparar com o mês anterior só mede a estação do ano.
Todas as comparações são com o mesmo período do ano anterior.

**Risco medido pelo ritmo de cada cliente, não por um prazo fixo.** Um cliente que
encomenda todas as semanas e está há 40 dias calado é um problema. Um que encomenda
de dois em dois meses, não. O cálculo usa a mediana do intervalo entre encomendas de
cada cliente e compara com o tempo que está sem comprar.

**Preço separado de volume.** A variação da faturação por categoria é decomposta em
quatro parcelas que somam exatamente o total:

```
efeito volume = preço antigo  ×  (quantidade nova − quantidade antiga)
efeito preço  = quantidade antiga × (preço novo − preço antigo)
efeito misto  = (variação de preço) × (variação de quantidade)
efeito gama   = produtos que só existem num dos períodos
```

É isto que distingue "estou a crescer" de "estou a cobrar mais caro a menos gente".
Há um teste automático que garante que as quatro parcelas fecham com a variação real.

**Estimativas com teto.** O "valor anual em jogo" de um cliente em risco nunca passa
o melhor ano que ele realmente fez. Não se apresenta a um empresário um número que
nunca existiu.

## Como usar

```bash
pip install -r requirements.txt

# gerar dados de demonstração (24 meses de uma empresa fictícia)
python -m saft_radar.gerar_demo demo/saft

# correr o Raio-X
python executar.py --saft demo/saft --saida saidas

# com ficheiros reais, e a escolher o mês
python executar.py --saft dados/cliente_x --mes 2026-07 --saida saidas/cliente_x
```

Sai três coisas para a pasta indicada:

- `painel.html` — relatório completo, abre em qualquer browser, não precisa de internet
- `raio-x.txt` — as mesmas conclusões em texto, para colar num email
- `power_bi/` — CSV em modelo estrela (factos + dimensões + calendário)

## Estrutura

```
saft_radar/
  leitor.py      lê SAF-T para DataFrames e confere os totais
  analise.py     KPIs, risco de perda, categorias, preço vs volume
  graficos.py    gráficos em SVG escritos à mão (sem dependências)
  estilo.py      CSS e JS do painel
  painel.py      monta o HTML e o texto do email
  exportar.py    CSV em modelo estrela para Power BI
  gerar_demo.py  gera SAF-T fictício para demonstração e testes
executar.py      linha de comandos
tests/           testes do leitor e da análise
```

Dependências: `pandas` e `numpy`. O painel não usa bibliotecas de gráficos — os SVG
são gerados diretamente, por isso o ficheiro abre sozinho daqui a dois anos.

## Testes

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

Os testes correm sobre SAF-T gerados na hora e verificam o que estraga um relatório
sem dar nas vistas: totais que não batem certo com o cabeçalho, documentos anulados
que entram na conta, notas de crédito com o sinal trocado, e a decomposição
preço/volume que não fecha.

## Proteção de dados

Um SAF-T tem o nome e o NIF dos clientes da empresa, por isso é dado pessoal ao
abrigo do RGPD. O `.gitignore` bloqueia `dados/`, `saidas/` e qualquer `.xml` ou
`.zip` fora de `docs/`. Antes de tratar ficheiros de uma empresa real é preciso um
contrato de subcontratante de tratamento de dados (artigo 28.º do RGPD).

Os dados de demonstração são gerados por código, com semente fixa. A empresa, os
clientes e os NIF são todos inventados.

## Licença

MIT.
