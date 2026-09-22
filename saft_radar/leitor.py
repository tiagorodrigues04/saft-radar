"""Leitor de ficheiros SAF-T (PT) versão 1.04_01.

Transforma uma pasta de ficheiros SAF-T em tabelas pandas prontas para análise.

Regras aplicadas (as que a maior parte das análises feitas à pressa esquece):
  * documentos anulados (InvoiceStatus = 'A' ou 'F') são excluídos;
  * notas de crédito (NC/NA) entram com sinal negativo;
  * os totais lidos são conferidos contra o cabeçalho de cada ficheiro;
  * valores são sempre líquidos de IVA (é o que interessa para analisar vendas).
"""
from __future__ import annotations

import gzip
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd

NS = "{urn:OECD:StandardAuditFile-Tax:PT_1.04_01}"

# Documentos que representam venda. NC/NA são devoluções (sinal negativo).
TIPOS_VENDA = {"FT": 1, "FS": 1, "FR": 1, "VD": 1, "ND": 1, "NC": -1, "NA": -1}
ESTADOS_INVALIDOS = {"A", "F"}  # anulado / faturado por outro doc


class ErroSAFT(Exception):
    """O ficheiro não é um SAF-T (PT) utilizável."""


@dataclass
class Dados:
    """Tudo o que foi lido, já limpo."""
    documentos: pd.DataFrame
    linhas: pd.DataFrame
    clientes: pd.DataFrame
    produtos: pd.DataFrame
    empresa: dict
    controlo: pd.DataFrame

    @property
    def periodo(self) -> tuple[pd.Timestamp, pd.Timestamp]:
        return self.documentos["data"].min(), self.documentos["data"].max()


def _texto(no, caminho: str, omissao: str = "") -> str:
    encontrado = no.find(caminho)
    if encontrado is None or encontrado.text is None:
        return omissao
    return encontrado.text.strip()


def _numero(no, caminho: str, omissao: float = 0.0) -> float:
    bruto = _texto(no, caminho)
    if not bruto:
        return omissao
    try:
        return float(bruto.replace(",", "."))
    except ValueError:
        return omissao


def _abrir(caminho: Path):
    """Aceita .xml, .xml.gz e .zip (um XML lá dentro)."""
    sufixo = caminho.suffix.lower()
    if sufixo == ".gz":
        return gzip.open(caminho, "rb")
    if sufixo == ".zip":
        arquivo = zipfile.ZipFile(caminho)
        nomes = [n for n in arquivo.namelist() if n.lower().endswith(".xml")]
        if not nomes:
            raise ErroSAFT(f"{caminho.name}: o zip não tem nenhum XML lá dentro")
        return arquivo.open(nomes[0])
    return open(caminho, "rb")


def ler_ficheiro(caminho: Path) -> dict:
    """Lê um SAF-T e devolve dicionários com documentos, linhas, clientes e produtos."""
    with _abrir(caminho) as f:
        try:
            raiz = ET.parse(f).getroot()
        except ET.ParseError as e:
            raise ErroSAFT(f"{caminho.name}: XML inválido ({e})") from e

    if not raiz.tag.endswith("AuditFile"):
        raise ErroSAFT(f"{caminho.name}: não parece um SAF-T (raiz = {raiz.tag})")

    cabecalho = raiz.find(f"{NS}Header")
    if cabecalho is None:
        raise ErroSAFT(f"{caminho.name}: sem Header")

    empresa = {
        "nif": _texto(cabecalho, f"{NS}TaxRegistrationNumber"),
        "nome": _texto(cabecalho, f"{NS}CompanyName"),
        "inicio": _texto(cabecalho, f"{NS}StartDate"),
        "fim": _texto(cabecalho, f"{NS}EndDate"),
        "moeda": _texto(cabecalho, f"{NS}CurrencyCode", "EUR"),
        "versao": _texto(cabecalho, f"{NS}AuditFileVersion"),
        "programa": _texto(cabecalho, f"{NS}ProductID"),
    }

    clientes = []
    for c in raiz.findall(f"{NS}MasterFiles/{NS}Customer"):
        clientes.append({
            "cliente_id": _texto(c, f"{NS}CustomerID"),
            "cliente_nome": _texto(c, f"{NS}CompanyName"),
            "cliente_nif": _texto(c, f"{NS}CustomerTaxID"),
            "cliente_local": _texto(c, f"{NS}BillingAddress/{NS}City"),
            "cliente_cp": _texto(c, f"{NS}BillingAddress/{NS}PostalCode"),
        })

    produtos = []
    for p in raiz.findall(f"{NS}MasterFiles/{NS}Product"):
        produtos.append({
            "produto_id": _texto(p, f"{NS}ProductCode"),
            "produto_nome": _texto(p, f"{NS}ProductDescription"),
            "categoria": _texto(p, f"{NS}ProductGroup") or "Sem categoria",
        })

    vendas = raiz.find(f"{NS}SourceDocuments/{NS}SalesInvoices")
    documentos, linhas = [], []
    declarado = {"n_docs": 0.0, "credito": 0.0, "debito": 0.0}

    if vendas is not None:
        declarado = {
            "n_docs": _numero(vendas, f"{NS}NumberOfEntries"),
            "credito": _numero(vendas, f"{NS}TotalCredit"),
            "debito": _numero(vendas, f"{NS}TotalDebit"),
        }
        for doc in vendas.findall(f"{NS}Invoice"):
            numero = _texto(doc, f"{NS}InvoiceNo")
            tipo = _texto(doc, f"{NS}InvoiceType")
            estado = _texto(doc, f"{NS}DocumentStatus/{NS}InvoiceStatus", "N")
            anulado = estado in ESTADOS_INVALIDOS
            sinal = TIPOS_VENDA.get(tipo, 1)
            net = _numero(doc, f"{NS}DocumentTotals/{NS}NetTotal")
            iva = _numero(doc, f"{NS}DocumentTotals/{NS}TaxPayable")
            data = _texto(doc, f"{NS}InvoiceDate")

            documentos.append({
                "documento": numero,
                "tipo": tipo,
                "estado": estado,
                "anulado": anulado,
                "data": data,
                "cliente_id": _texto(doc, f"{NS}CustomerID"),
                "liquido": sinal * net,
                "iva": sinal * iva,
                "total": sinal * (net + iva),
                "ficheiro": caminho.name,
            })

            for linha in doc.findall(f"{NS}Line"):
                credito = _numero(linha, f"{NS}CreditAmount")
                debito = _numero(linha, f"{NS}DebitAmount")
                valor = credito - debito
                linhas.append({
                    "documento": numero,
                    "tipo": tipo,
                    "anulado": anulado,
                    "data": data,
                    "cliente_id": _texto(doc, f"{NS}CustomerID"),
                    "produto_id": _texto(linha, f"{NS}ProductCode"),
                    "produto_nome": _texto(linha, f"{NS}ProductDescription"),
                    "quantidade": sinal * _numero(linha, f"{NS}Quantity"),
                    "preco_unitario": _numero(linha, f"{NS}UnitPrice"),
                    "liquido": sinal * valor if tipo not in ("NC", "NA") else -abs(valor),
                    "taxa_iva": _texto(linha, f"{NS}Tax/{NS}TaxCode"),
                })

    return {
        "empresa": empresa,
        "clientes": clientes,
        "produtos": produtos,
        "documentos": documentos,
        "linhas": linhas,
        "declarado": declarado,
    }


def ler_pasta(pasta: Path, padrao: str = "*") -> Dados:
    """Lê todos os SAF-T de uma pasta e devolve tabelas já limpas."""
    pasta = Path(pasta)
    if not pasta.exists():
        raise ErroSAFT(f"A pasta {pasta} não existe.")

    ficheiros = sorted(
        p for p in pasta.glob(padrao)
        if p.suffix.lower() in {".xml", ".gz", ".zip"} and p.is_file()
    )
    if not ficheiros:
        raise ErroSAFT(f"Não encontrei ficheiros SAF-T em {pasta}.")

    docs, lins, clis, prods, controlo = [], [], [], [], []
    empresa: dict = {}

    for caminho in ficheiros:
        lido = ler_ficheiro(caminho)
        if not empresa:
            empresa = lido["empresa"]
        elif empresa["nif"] != lido["empresa"]["nif"]:
            raise ErroSAFT(
                "A pasta tem ficheiros de empresas diferentes "
                f"({empresa['nif']} e {lido['empresa']['nif']}). Separe-os por pasta."
            )
        docs.extend(lido["documentos"])
        lins.extend(lido["linhas"])
        clis.extend(lido["clientes"])
        prods.extend(lido["produtos"])

        validos = [d for d in lido["documentos"] if not d["anulado"]]
        lido_liquido = round(sum(d["liquido"] for d in validos), 2)
        declarado_liquido = round(lido["declarado"]["credito"] - lido["declarado"]["debito"], 2)
        controlo.append({
            "ficheiro": caminho.name,
            "periodo": lido["empresa"]["inicio"][:7],
            "docs_declarados": int(lido["declarado"]["n_docs"]),
            "docs_lidos": len(lido["documentos"]),
            "anulados": len(lido["documentos"]) - len(validos),
            "liquido_declarado": declarado_liquido,
            "liquido_lido": lido_liquido,
            "diferenca": round(lido_liquido - declarado_liquido, 2),
        })

    documentos = pd.DataFrame(docs)
    linhas = pd.DataFrame(lins)
    if documentos.empty:
        raise ErroSAFT("Os ficheiros não têm documentos de venda.")

    for tabela in (documentos, linhas):
        tabela["data"] = pd.to_datetime(tabela["data"], errors="coerce")

    documentos = documentos[~documentos["anulado"]].drop(columns=["anulado"])
    linhas = linhas[~linhas["anulado"]].drop(columns=["anulado"])
    documentos = documentos.dropna(subset=["data"])
    linhas = linhas.dropna(subset=["data"])

    # o mesmo documento pode repetir-se se houver ficheiros sobrepostos
    documentos = documentos.drop_duplicates(subset=["documento"], keep="first")
    linhas = linhas[linhas["documento"].isin(set(documentos["documento"]))]

    clientes = pd.DataFrame(clis).drop_duplicates(subset=["cliente_id"], keep="last")
    produtos = pd.DataFrame(prods).drop_duplicates(subset=["produto_id"], keep="last")

    for tabela in (documentos, linhas):
        tabela["mes"] = tabela["data"].dt.to_period("M").astype(str)

    linhas = linhas.merge(produtos[["produto_id", "categoria"]], on="produto_id", how="left")
    linhas["categoria"] = linhas["categoria"].fillna("Sem categoria")
    nomes = clientes[["cliente_id", "cliente_nome"]]
    documentos = documentos.merge(nomes, on="cliente_id", how="left")
    linhas = linhas.merge(nomes, on="cliente_id", how="left")
    for tabela in (documentos, linhas):
        tabela["cliente_nome"] = tabela["cliente_nome"].fillna("(cliente sem ficha)")

    return Dados(
        documentos=documentos.reset_index(drop=True),
        linhas=linhas.reset_index(drop=True),
        clientes=clientes.reset_index(drop=True),
        produtos=produtos.reset_index(drop=True),
        empresa=empresa,
        controlo=pd.DataFrame(controlo),
    )
