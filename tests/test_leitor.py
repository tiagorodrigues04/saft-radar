"""Testes do leitor — a parte onde um erro passa despercebido e estraga tudo."""
from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from saft_radar.analise import analisar
from saft_radar.gerar_demo import gerar
from saft_radar.leitor import ErroSAFT, ler_ficheiro, ler_pasta

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def pasta_saft(tmp_path_factory):
    destino = tmp_path_factory.mktemp("saft")
    gerar(destino)
    return destino


@pytest.fixture(scope="module")
def dados(pasta_saft):
    return ler_pasta(pasta_saft)


def test_le_todos_os_ficheiros(dados):
    assert dados.controlo["ficheiro"].nunique() == 24
    assert len(dados.documentos) > 5000
    assert len(dados.linhas) > 20000


def test_totais_batem_certo_com_o_cabecalho(dados):
    """Se isto falhar, o número que vai para o cliente está errado."""
    assert (dados.controlo["diferenca"].abs() < 0.01).all()


def test_documentos_anulados_sao_excluidos(pasta_saft, dados):
    bruto = ler_ficheiro(sorted(pasta_saft.glob("*.xml"))[0])
    anulados = [d["documento"] for d in bruto["documentos"] if d["anulado"]]
    assert anulados, "o gerador tem de produzir alguns documentos anulados"
    assert not set(anulados) & set(dados.documentos["documento"])


def test_notas_de_credito_entram_negativas(dados):
    nc = dados.documentos[dados.documentos["tipo"] == "NC"]
    assert len(nc) > 0
    assert (nc["liquido"] < 0).all()


def test_linhas_e_documentos_dao_o_mesmo_total(dados):
    assert dados.documentos["liquido"].sum() == pytest.approx(
        dados.linhas["liquido"].sum(), abs=0.05)


def test_sem_documentos_repetidos(dados):
    assert dados.documentos["documento"].is_unique


def test_toda_a_linha_tem_categoria(dados):
    assert dados.linhas["categoria"].notna().all()
    assert (dados.linhas["categoria"] != "").all()


def test_le_ficheiros_comprimidos(pasta_saft, tmp_path):
    origem = sorted(pasta_saft.glob("*.xml"))[0]
    destino = tmp_path / (origem.name + ".gz")
    destino.write_bytes(gzip.compress(origem.read_bytes()))
    assert ler_ficheiro(destino)["empresa"]["nif"] == ler_ficheiro(origem)["empresa"]["nif"]


def test_pasta_vazia_da_erro_claro(tmp_path):
    with pytest.raises(ErroSAFT, match="Não encontrei"):
        ler_pasta(tmp_path)


def test_ficheiro_que_nao_e_saft_da_erro_claro(tmp_path):
    mau = tmp_path / "coisa.xml"
    mau.write_text("<outra_coisa><a/></outra_coisa>", encoding="utf-8")
    with pytest.raises(ErroSAFT, match="não parece um SAF-T"):
        ler_ficheiro(mau)


def test_empresas_diferentes_na_mesma_pasta(pasta_saft, tmp_path):
    origem = sorted(pasta_saft.glob("*.xml"))[0]
    (tmp_path / origem.name).write_bytes(origem.read_bytes())
    trocado = origem.read_text(encoding="utf-8").replace("504827391", "999888777")
    (tmp_path / "outra.xml").write_text(trocado, encoding="utf-8")
    with pytest.raises(ErroSAFT, match="empresas diferentes"):
        ler_pasta(tmp_path)


# ------------------------------------------------------------------- análise

def test_analise_usa_o_ultimo_mes(dados):
    a = analisar(dados)
    assert a.mes == sorted(dados.documentos["mes"].unique())[-1]


def test_preco_volume_reconcilia(dados):
    """Os efeitos têm de somar exatamente a variação da faturação."""
    pv = analisar(dados).preco_volume
    soma = pv["ef_volume"] + pv["ef_preco"] + pv["ef_misto"] + pv["ef_gama"]
    assert soma.round(2).tolist() == pv["diferenca"].round(2).tolist()


def test_valor_em_risco_nunca_inventa_numeros(dados):
    """A estimativa anual não pode passar o melhor ano que o cliente fez."""
    c = analisar(dados).clientes
    teto = c[["valor_12m", "valor_12m_anterior"]].max(axis=1)
    assert (c["valor_anual_estimado"] <= teto + 0.01).all()


def test_mes_inexistente_da_erro_claro(dados):
    with pytest.raises(ValueError, match="não existe nos dados"):
        analisar(dados, "1999-01")


def test_achados_tem_sempre_titulo_e_texto(dados):
    for ach in analisar(dados).achados:
        assert ach["titulo"] and ach["texto"]
        assert ach["tipo"] in {"alerta", "positivo", "info"}
