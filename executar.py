#!/usr/bin/env python3
"""Raio-X de vendas a partir de ficheiros SAF-T.

    python executar.py                      # usa os dados de demonstração
    python executar.py --saft dados/cliente_x --saida saidas/cliente_x
    python executar.py --saft dados/cliente_x --mes 2026-07
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from saft_radar.analise import analisar, mes_extenso
from saft_radar.exportar import exportar
from saft_radar.leitor import ErroSAFT, ler_pasta
from saft_radar.painel import gerar_html, texto_raio_x


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Raio-X mensal a partir de ficheiros SAF-T")
    p.add_argument("--saft", default="demo/saft",
                   help="pasta com os ficheiros SAF-T (.xml, .xml.gz ou .zip)")
    p.add_argument("--saida", default="saidas", help="pasta onde escrever os resultados")
    p.add_argument("--mes", default=None, help="mês a analisar, AAAA-MM (por omissão, o último)")
    p.add_argument("--sem-csv", action="store_true", help="não exportar os CSV para Power BI")
    a = p.parse_args(argv)

    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)

    try:
        print(f"A ler os ficheiros SAF-T de {a.saft} ...")
        dados = ler_pasta(Path(a.saft))
    except ErroSAFT as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1

    inicio, fim = dados.periodo
    print(f"  {dados.empresa['nome']} (NIF {dados.empresa['nif']})")
    print(f"  {len(dados.documentos)} documentos e {len(dados.linhas)} linhas, "
          f"de {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}")

    diferencas = dados.controlo[dados.controlo["diferenca"].abs() > 0.01]
    if len(diferencas):
        print(f"  Atenção: {len(diferencas)} ficheiro(s) não batem certo com o "
              f"próprio cabeçalho. Ver controlo_saft.csv.")
    else:
        print("  Totais conferidos com o cabeçalho de todos os ficheiros.")

    try:
        analise = analisar(dados, a.mes)
    except ValueError as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1

    painel = saida / "painel.html"
    painel.write_text(gerar_html(analise), encoding="utf-8")
    (saida / "raio-x.txt").write_text(texto_raio_x(analise), encoding="utf-8")
    dados.controlo.to_csv(saida / "controlo_saft.csv", index=False,
                          encoding="utf-8-sig", sep=";", decimal=",")

    if not a.sem_csv:
        exportar(dados, analise, saida / "power_bi")

    print(f"\nRaio-X de {mes_extenso(analise.mes)}:")
    for ach in analise.achados:
        print(f"  · {ach['titulo']}")
    print(f"\nPainel:  {painel}")
    print(f"Email:   {saida / 'raio-x.txt'}")
    if not a.sem_csv:
        print(f"Power BI: {saida / 'power_bi'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
