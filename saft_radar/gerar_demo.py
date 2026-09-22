"""Gera ficheiros SAF-T (PT) fictícios de uma distribuidora alimentar.

Serve para demonstrar o Raio-X sem usar dados reais de nenhum cliente.
Os dados são gerados com semente fixa, por isso são sempre iguais.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

SEMENTE = 20260922
NIF_EMPRESA = "504827391"
NOME_EMPRESA = "Distribuidora Alimentar Vale do Mondego, Lda"

# 24 meses completos: setembro/2024 a agosto/2026
PRIMEIRO_MES = (2024, 9)
N_MESES = 24

IVA = {"NOR": 23.0, "INT": 13.0, "RED": 6.0}

# nome: (taxa iva, nº produtos, preço min, preço max,
#        tendência anual de VOLUME, tendência anual de PREÇO, sazonalidade)
CATEGORIAS = {
    "Bebidas": ("NOR", 26, 0.65, 38.0, -0.05, 0.055, "verao"),
    "Mercearia": ("RED", 30, 0.80, 24.0, 0.01, 0.020, "plana"),
    "Congelados": ("RED", 18, 2.20, 46.0, -0.02, 0.030, "inverno"),
    "Laticínios": ("RED", 14, 1.10, 19.5, 0.00, 0.025, "plana"),
    "Descartáveis e Higiene": ("NOR", 16, 1.40, 62.0, -0.19, 0.015, "verao"),
    "Padaria e Pastelaria": ("INT", 12, 0.95, 16.0, 0.21, 0.020, "plana"),
}

TIPOS_CLIENTE = ["Restaurante", "Café / Snack-bar", "Hotelaria", "Mercearia / Loja", "Cantina"]

PRIMEIROS = ["Sabor", "Casa", "Retiro", "Recanto", "Quinta", "Solar", "Taberna", "Adega", "Cantinho",
             "Terraço", "Pátio", "Forno", "Mesa", "Varanda", "Praça", "Largo", "Ponte",
             "Miradouro", "Jardim", "Fonte", "Moinho", "Celeiro", "Alecrim", "Oliveira"]
SEGUNDOS = ["do Mondego", "da Serra", "de Coimbra", "Velho", "Novo", "do Rio", "Real",
            "das Flores", "do Norte", "Dourado", "da Vila", "do Campo", "de Cima",
            "Antigo", "Central", "da Estrela", "do Vale", "Feliz", "da Praça", "Azul"]
FORMAS = ["Lda", "Unipessoal Lda", "SA", ""]

CONCELHOS = ["Coimbra", "Figueira da Foz", "Cantanhede", "Montemor-o-Velho", "Mealhada",
             "Condeixa-a-Nova", "Penacova", "Lousã", "Soure", "Mira", "Anadia", "Águeda"]

PRODUTOS_BASE = {
    "Bebidas": ["Água mineral 1,5L", "Água mineral 0,33L", "Refrigerante cola 1,5L",
                "Refrigerante laranja 0,25L", "Cerveja barril 30L", "Cerveja 0,33L",
                "Vinho tinto regional", "Vinho verde branco", "Sumo néctar pêssego",
                "Chá gelado limão", "Água tónica", "Vinho do Porto", "Aguardente velha",
                "Whisky reserva", "Gin importado", "Licor de ervas", "Vodka", "Rum branco",
                "Espumante bruto", "Café em grão 1kg", "Cápsulas de café", "Leite achocolatado",
                "Bebida energética", "Sidra", "Vinho rosé", "Água das pedras"],
    "Mercearia": ["Arroz agulha 5kg", "Massa esparguete 3kg", "Azeite virgem 5L",
                  "Óleo alimentar 10L", "Açúcar branco 10kg", "Sal grosso 5kg",
                  "Farinha tipo 65 25kg", "Atum em lata 1kg", "Tomate pelado 2,5kg",
                  "Grão-de-bico 2,5kg", "Feijão encarnado 2,5kg", "Milho doce 2,5kg",
                  "Ketchup 2L", "Maionese 2L", "Mostarda 1L", "Vinagre de vinho 5L",
                  "Piri-piri 1L", "Molho de soja 1L", "Batata frita pacote", "Amendoins 1kg",
                  "Bolachas água e sal", "Cereais pequeno-almoço", "Compota morango 1kg",
                  "Mel 1kg", "Chocolate culinária 1kg", "Noodles instantâneos",
                  "Caldo de galinha", "Orégãos 200g", "Canela em pó 200g", "Colorau 500g"],
    "Congelados": ["Batata pré-frita 2,5kg", "Bacalhau demolhado 1kg", "Pescada filetes 2kg",
                   "Camarão 30/40 1kg", "Lulas anéis 1kg", "Hambúrguer bovino 2kg",
                   "Frango panado 2kg", "Nuggets 2kg", "Rissóis camarão 60un",
                   "Croquetes carne 60un", "Legumes salteados 2,5kg", "Ervilhas 2,5kg",
                   "Espinafres 2,5kg", "Pizza base 5un", "Gelado balde 5L",
                   "Polvo congelado 2kg", "Salmão lombos 2kg", "Pataniscas 1kg"],
    "Laticínios": ["Leite UHT meio-gordo 12x1L", "Leite UHT magro 12x1L", "Manteiga 1kg",
                   "Queijo flamengo bola", "Queijo ralado 1kg", "Queijo fatiado 1kg",
                   "Natas culinárias 12x1L", "Iogurte natural 16un", "Iogurte aromas 16un",
                   "Requeijão 6un", "Queijo fresco 12un", "Mozzarella 2,5kg",
                   "Creme pasteleiro 1kg", "Leite condensado 1kg"],
    "Descartáveis e Higiene": ["Guardanapos 30x30 2400un", "Toalhetes mão 3000un",
                               "Papel higiénico 40rolos", "Copos plástico 3000un",
                               "Talheres descartáveis 1000un", "Embalagens take-away 500un",
                               "Sacos plástico 1000un", "Filme aderente 300m",
                               "Papel alumínio 150m", "Detergente loiça 20L",
                               "Desengordurante 5L", "Lixívia 20L", "Luvas latex 1000un",
                               "Sacos lixo 100L 200un", "Toalhas de mesa papel",
                               "Palhinhas papel 5000un"],
    "Padaria e Pastelaria": ["Pão cacete 40un", "Pão de forma 10un", "Broa de milho 12un",
                            "Bolo de arroz 24un", "Pastel de nata 60un", "Croissant 40un",
                            "Tosta pão 20un", "Queques 24un", "Bolo rei 6un",
                            "Pão de leite 50un", "Folhado misto 30un", "Baguete 30un"],
}


@dataclass
class Cliente:
    codigo: str
    nome: str
    nif: str
    concelho: str
    tipo: str
    base_mensal: float          # euros/mês em condições normais
    encomendas_mes: float       # nº médio de encomendas por mês
    perfil: str                 # estavel | perdido | queda | crescimento | novo
    mes_corte: int = 99         # mês (índice) a partir do qual deixa de comprar
    pesos: dict = field(default_factory=dict)


@dataclass
class Produto:
    codigo: str
    nome: str
    categoria: str
    taxa: str
    preco: float
    mes_entrada: int = 0     # só passa a ser vendido a partir deste mês
    mes_saida: int = 99      # deixa de ser vendido a partir deste mês


def _mes_para_data(indice: int) -> tuple[int, int]:
    ano, mes = PRIMEIRO_MES
    total = (ano * 12 + (mes - 1)) + indice
    return total // 12, total % 12 + 1


def _ultimo_dia(ano: int, mes: int) -> int:
    if mes == 12:
        return 31
    return (date(ano, mes + 1, 1) - timedelta(days=1)).day


def _sazonal(perfil: str, mes: int) -> float:
    """Multiplicador sazonal do mês (1..12)."""
    verao = {1: 0.78, 2: 0.82, 3: 0.92, 4: 1.00, 5: 1.06, 6: 1.18,
             7: 1.34, 8: 1.42, 9: 1.12, 10: 0.96, 11: 0.90, 12: 1.05}
    inverno = {1: 1.18, 2: 1.14, 3: 1.06, 4: 0.98, 5: 0.90, 6: 0.84,
               7: 0.80, 8: 0.82, 9: 0.94, 10: 1.04, 11: 1.12, 12: 1.20}
    plana = {1: 0.88, 2: 0.92, 3: 0.98, 4: 1.00, 5: 1.02, 6: 1.06,
             7: 1.12, 8: 1.14, 9: 1.02, 10: 0.98, 11: 0.96, 12: 1.06}
    return {"verao": verao, "inverno": inverno, "plana": plana}[perfil][mes]


def _gerar_nif(rng: random.Random) -> str:
    return str(rng.choice([5, 5, 5, 2]) * 100000000 + rng.randint(1000000, 9999999))


def construir_clientes(rng: random.Random) -> list[Cliente]:
    usados: set[str] = set()
    clientes: list[Cliente] = []
    n = 148
    for i in range(n):
        while True:
            nome = f"{rng.choice(PRIMEIROS)} {rng.choice(SEGUNDOS)}"
            forma = rng.choice(FORMAS)
            nome_completo = f"{nome} {forma}".strip() if forma else nome
            if nome_completo not in usados:
                usados.add(nome_completo)
                break
        tipo = rng.choices(TIPOS_CLIENTE, weights=[38, 30, 12, 15, 5])[0]
        escala = {"Restaurante": 1.0, "Café / Snack-bar": 0.55, "Hotelaria": 2.6,
                  "Mercearia / Loja": 0.85, "Cantina": 1.9}[tipo]
        base = rng.lognormvariate(5.95, 0.88) * escala
        base = min(max(base, 90), 9500)
        encomendas = max(0.7, min(9.0, rng.gauss(2.6, 1.1) * (1.4 if escala > 1.5 else 1.0)))

        r = rng.random()
        if r < 0.115:
            perfil = "perdido"
            corte = rng.randint(9, 20)
        elif r < 0.245:
            perfil = "queda"
            corte = 99
        elif r < 0.375:
            perfil = "crescimento"
            corte = 99
        elif r < 0.445:
            perfil = "novo"
            corte = 99
        else:
            perfil = "estavel"
            corte = 99

        pesos = {}
        for cat in CATEGORIAS:
            p = rng.random() ** 1.6
            pesos[cat] = p
        if tipo == "Café / Snack-bar":
            pesos["Bebidas"] += 1.4
            pesos["Padaria e Pastelaria"] += 1.0
        elif tipo == "Restaurante":
            pesos["Congelados"] += 1.1
            pesos["Mercearia"] += 0.9
        elif tipo == "Hotelaria":
            pesos["Laticínios"] += 0.8
            pesos["Descartáveis e Higiene"] += 0.9
        elif tipo == "Mercearia / Loja":
            pesos["Mercearia"] += 1.3
            pesos["Laticínios"] += 0.7
        total = sum(pesos.values())
        pesos = {k: v / total for k, v in pesos.items()}

        clientes.append(Cliente(
            codigo=f"C{2000 + i}",
            nome=nome_completo,
            nif=_gerar_nif(rng),
            concelho=rng.choice(CONCELHOS),
            tipo=tipo,
            base_mensal=round(base, 2),
            encomendas_mes=round(encomendas, 2),
            perfil=perfil,
            mes_corte=corte,
            pesos=pesos,
        ))
    return clientes


def construir_produtos(rng: random.Random) -> list[Produto]:
    produtos: list[Produto] = []
    i = 0
    for cat, (taxa, n, pmin, pmax, _tv, _tp, _saz) in CATEGORIAS.items():
        nomes = PRODUTOS_BASE[cat]
        for j in range(n):
            nome = nomes[j % len(nomes)]
            if j >= len(nomes):
                nome = f"{nome} (formato grande)"
            preco = round(pmin + (pmax - pmin) * rng.random() ** 1.7, 2)
            entrada, saida = 0, 99
            sorte = rng.random()
            if sorte < 0.09:                       # produto novo na gama
                entrada = rng.randint(13, 20)
            elif sorte < 0.17:                     # produto descontinuado
                saida = rng.randint(12, 20)
            produtos.append(Produto(f"P{1000 + i}", nome, cat, taxa, max(preco, 0.45),
                                    entrada, saida))
            i += 1
    return produtos


def _fator_cliente(c: Cliente, m: int) -> float:
    if c.perfil == "perdido":
        if m >= c.mes_corte:
            return 0.0
        if m >= c.mes_corte - 2:
            return 0.55
        return 1.0
    if c.perfil == "queda":
        return max(0.25, 1.0 - 0.030 * m)
    if c.perfil == "crescimento":
        return 1.0 + 0.032 * m
    if c.perfil == "novo":
        inicio = 5 + (int(c.codigo[1:]) * 7 % 16)
        if m < inicio:
            return 0.0
        return min(1.25, 0.35 + 0.09 * (m - inicio))
    return 1.0


def _hash_doc(anterior: str, chave: str) -> str:
    h = hashlib.sha1(f"{anterior}|{chave}".encode()).digest()
    import base64
    return base64.b64encode(h * 6).decode()[:172]


def gerar(destino: Path) -> dict:
    rng = random.Random(SEMENTE)
    clientes = construir_clientes(rng)
    produtos = construir_produtos(rng)
    por_cat: dict[str, list[Produto]] = {}
    for p in produtos:
        por_cat.setdefault(p.categoria, []).append(p)

    destino.mkdir(parents=True, exist_ok=True)
    for antigo in destino.glob("SAFT_*.xml"):
        antigo.unlink()

    resumo = {"ficheiros": 0, "faturas": 0, "notas_credito": 0, "anulados": 0, "liquido": 0.0}
    contador = {"FT": 0, "NC": 0}
    hash_ant = ""

    for m in range(N_MESES):
        ano, mes = _mes_para_data(m)
        docs: list[str] = []
        n_docs = 0
        total_credito = 0.0
        total_debito = 0.0

        for c in clientes:
            fator = _fator_cliente(c, m)
            if fator <= 0:
                continue
            n_enc = rng.gauss(c.encomendas_mes * fator, 0.6)
            n_enc = max(0, round(n_enc))
            for _ in range(n_enc):
                dia = rng.randint(1, _ultimo_dia(ano, mes))
                data_doc = date(ano, mes, dia)
                linhas_xml = []
                net = 0.0
                iva_total = 0.0
                n_linhas = max(1, round(rng.gauss(5.5, 2.6)))
                cats = rng.choices(list(c.pesos.keys()), weights=list(c.pesos.values()),
                                   k=n_linhas)
                valor_alvo = c.base_mensal * fator / max(c.encomendas_mes, 0.5)
                for ln, cat in enumerate(cats, start=1):
                    disponiveis = [p for p in por_cat[cat]
                                   if p.mes_entrada <= m < p.mes_saida]
                    if not disponiveis:
                        continue
                    prod = rng.choice(disponiveis)
                    _, _, _, _, tend_vol, tend_preco, perfil_saz = CATEGORIAS[cat]
                    saz = _sazonal(perfil_saz, mes)
                    # A QUANTIDADE vem da procura e usa sempre o preço-base,
                    # para não reagir à variação de preços (senão preço e volume
                    # anulavam-se e a decomposição não dizia nada).
                    alvo_linha = valor_alvo * saz / n_linhas * (1 + tend_vol * (m / 12))
                    qtd = max(1, round(alvo_linha / max(prod.preco, 0.5)))
                    qtd = min(qtd, 220)
                    # O PREÇO varia por tendência da categoria, à parte da quantidade.
                    preco = prod.preco * (1 + tend_preco * (m / 12))
                    preco = round(preco * rng.uniform(0.985, 1.02), 2)
                    valor = round(qtd * preco, 2)
                    net += valor
                    iva_total += round(valor * IVA[prod.taxa] / 100, 2)
                    linhas_xml.append(_linha_xml(ln, prod, qtd, preco, valor, data_doc, "C"))
                if net <= 0:
                    continue
                net = round(net, 2)
                iva_total = round(iva_total, 2)
                contador["FT"] += 1
                numero = f"FT FA2024/{contador['FT']}"
                # ~1,3% dos documentos são anulados (têm de ser excluídos da análise)
                anulado = rng.random() < 0.013
                estado = "A" if anulado else "N"
                hash_ant = _hash_doc(hash_ant, numero)
                docs.append(_doc_xml("Invoice", numero, estado, "FT", data_doc, mes,
                                     c.codigo, linhas_xml, iva_total, net, hash_ant))
                n_docs += 1
                if not anulado:
                    total_credito += net
                    resumo["liquido"] += net
                    resumo["faturas"] += 1
                else:
                    resumo["anulados"] += 1

        # notas de crédito (devoluções) — concentradas nalguns produtos/clientes
        n_nc = max(1, round(n_docs * 0.022))
        for _ in range(n_nc):
            c = rng.choice([x for x in clientes if _fator_cliente(x, m) > 0])
            dia = rng.randint(1, _ultimo_dia(ano, mes))
            data_doc = date(ano, mes, dia)
            cat = rng.choices(["Congelados", "Laticínios", "Bebidas", "Mercearia"],
                              weights=[46, 26, 16, 12])[0]
            ativos = [p for p in por_cat[cat] if p.mes_entrada <= m < p.mes_saida]
            prod = rng.choice(ativos or por_cat[cat])
            qtd = rng.randint(1, 8)
            preco = round(prod.preco * rng.uniform(0.98, 1.05), 2)
            valor = round(qtd * preco, 2)
            iva_total = round(valor * IVA[prod.taxa] / 100, 2)
            contador["NC"] += 1
            numero = f"NC NC2024/{contador['NC']}"
            hash_ant = _hash_doc(hash_ant, numero)
            linha = _linha_xml(1, prod, qtd, preco, valor, data_doc, "D")
            docs.append(_doc_xml("Invoice", numero, "N", "NC", data_doc, mes,
                                 c.codigo, [linha], iva_total, valor, hash_ant,
                                 referencia=f"FT FA2024/{max(1, contador['FT'] - rng.randint(1, 40))}"))
            n_docs += 1
            total_debito += valor
            resumo["liquido"] -= valor
            resumo["notas_credito"] += 1

        xml = _ficheiro_xml(ano, mes, clientes, produtos, docs, n_docs,
                            total_debito, total_credito)
        caminho = destino / f"SAFT_{ano}{mes:02d}.xml"
        caminho.write_text(xml, encoding="utf-8")
        resumo["ficheiros"] += 1

    resumo["liquido"] = round(resumo["liquido"], 2)
    resumo["clientes"] = len(clientes)
    resumo["produtos"] = len(produtos)
    return resumo


def _linha_xml(n: int, prod: Produto, qtd: int, preco: float, valor: float,
               data_doc: date, sinal: str) -> str:
    campo = "CreditAmount" if sinal == "C" else "DebitAmount"
    return f"""            <Line>
                <LineNumber>{n}</LineNumber>
                <ProductCode>{prod.codigo}</ProductCode>
                <ProductDescription>{escape(prod.nome)}</ProductDescription>
                <Quantity>{qtd}.00</Quantity>
                <UnitOfMeasure>UN</UnitOfMeasure>
                <UnitPrice>{preco:.2f}</UnitPrice>
                <TaxPointDate>{data_doc.isoformat()}</TaxPointDate>
                <Description>{escape(prod.nome)}</Description>
                <{campo}>{valor:.2f}</{campo}>
                <Tax>
                    <TaxType>IVA</TaxType>
                    <TaxCountryRegion>PT</TaxCountryRegion>
                    <TaxCode>{prod.taxa}</TaxCode>
                    <TaxPercentage>{IVA[prod.taxa]:.2f}</TaxPercentage>
                </Tax>
            </Line>"""


def _doc_xml(tag: str, numero: str, estado: str, tipo: str, data_doc: date, periodo: int,
             cliente: str, linhas: list[str], iva: float, net: float, hash_doc: str,
             referencia: str | None = None) -> str:
    ref = ""
    if referencia:
        ref = f"""
                <References>
                    <Reference>{escape(referencia)}</Reference>
                    <Reason>Devolução de mercadoria</Reason>
                </References>"""
    hora = f"{data_doc.isoformat()}T{9 + (hash(numero) % 9):02d}:{hash(numero) % 60:02d}:00"
    return f"""        <{tag}>
            <InvoiceNo>{escape(numero)}</InvoiceNo>
            <DocumentStatus>
                <InvoiceStatus>{estado}</InvoiceStatus>
                <InvoiceStatusDate>{hora}</InvoiceStatusDate>
                <SourceID>1</SourceID>
                <SourceBilling>P</SourceBilling>
            </DocumentStatus>
            <Hash>{hash_doc}</Hash>
            <HashControl>1</HashControl>
            <Period>{periodo}</Period>
            <InvoiceDate>{data_doc.isoformat()}</InvoiceDate>
            <InvoiceType>{tipo}</InvoiceType>
            <SpecialRegimes>
                <SelfBillingIndicator>0</SelfBillingIndicator>
                <CashVATSchemeIndicator>0</CashVATSchemeIndicator>
                <ThirdPartiesBillingIndicator>0</ThirdPartiesBillingIndicator>
            </SpecialRegimes>
            <SourceID>1</SourceID>
            <SystemEntryDate>{hora}</SystemEntryDate>
            <CustomerID>{cliente}</CustomerID>{ref}
{chr(10).join(linhas)}
            <DocumentTotals>
                <TaxPayable>{iva:.2f}</TaxPayable>
                <NetTotal>{net:.2f}</NetTotal>
                <GrossTotal>{net + iva:.2f}</GrossTotal>
            </DocumentTotals>
        </{tag}>"""


def _ficheiro_xml(ano: int, mes: int, clientes: list[Cliente], produtos: list[Produto],
                  docs: list[str], n_docs: int, debito: float, credito: float) -> str:
    fim = date(ano, mes, _ultimo_dia(ano, mes))
    cli_xml = "\n".join(
        f"""        <Customer>
            <CustomerID>{c.codigo}</CustomerID>
            <AccountID>Desconhecido</AccountID>
            <CustomerTaxID>{c.nif}</CustomerTaxID>
            <CompanyName>{escape(c.nome)}</CompanyName>
            <BillingAddress>
                <AddressDetail>Rua Principal, {hash(c.codigo) % 300 + 1}</AddressDetail>
                <City>{escape(c.concelho)}</City>
                <PostalCode>{3000 + hash(c.codigo) % 800}-{hash(c.nome) % 900 + 99:03d}</PostalCode>
                <Country>PT</Country>
            </BillingAddress>
            <SelfBillingIndicator>0</SelfBillingIndicator>
        </Customer>""" for c in clientes)
    prod_xml = "\n".join(
        f"""        <Product>
            <ProductType>P</ProductType>
            <ProductCode>{p.codigo}</ProductCode>
            <ProductGroup>{escape(p.categoria)}</ProductGroup>
            <ProductDescription>{escape(p.nome)}</ProductDescription>
            <ProductNumberCode>{p.codigo}</ProductNumberCode>
        </Product>""" for p in produtos)
    taxas = "\n".join(
        f"""        <TaxTableEntry>
            <TaxType>IVA</TaxType>
            <TaxCountryRegion>PT</TaxCountryRegion>
            <TaxCode>{cod}</TaxCode>
            <Description>IVA taxa {cod}</Description>
            <TaxPercentage>{pct:.2f}</TaxPercentage>
        </TaxTableEntry>""" for cod, pct in IVA.items())

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:PT_1.04_01">
    <Header>
        <AuditFileVersion>1.04_01</AuditFileVersion>
        <CompanyID>{NIF_EMPRESA}</CompanyID>
        <TaxRegistrationNumber>{NIF_EMPRESA}</TaxRegistrationNumber>
        <TaxAccountingBasis>F</TaxAccountingBasis>
        <CompanyName>{escape(NOME_EMPRESA)}</CompanyName>
        <CompanyAddress>
            <AddressDetail>Zona Industrial da Pedrulha, Lote 14</AddressDetail>
            <City>Coimbra</City>
            <PostalCode>3025-186</PostalCode>
            <Country>PT</Country>
        </CompanyAddress>
        <FiscalYear>{ano}</FiscalYear>
        <StartDate>{date(ano, mes, 1).isoformat()}</StartDate>
        <EndDate>{fim.isoformat()}</EndDate>
        <CurrencyCode>EUR</CurrencyCode>
        <DateCreated>{(fim + timedelta(days=3)).isoformat()}</DateCreated>
        <TaxEntity>Global</TaxEntity>
        <ProductCompanyTaxID>500000000</ProductCompanyTaxID>
        <SoftwareCertificateNumber>0000</SoftwareCertificateNumber>
        <ProductID>DemoFact/DemoSoft</ProductID>
        <ProductVersion>1.0</ProductVersion>
    </Header>
    <MasterFiles>
{cli_xml}
{prod_xml}
        <TaxTable>
{taxas}
        </TaxTable>
    </MasterFiles>
    <SourceDocuments>
        <SalesInvoices>
            <NumberOfEntries>{n_docs}</NumberOfEntries>
            <TotalDebit>{debito:.2f}</TotalDebit>
            <TotalCredit>{credito:.2f}</TotalCredit>
{chr(10).join(docs)}
        </SalesInvoices>
    </SourceDocuments>
</AuditFile>
"""


if __name__ == "__main__":
    import sys
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("demo/saft")
    print(gerar(destino))
