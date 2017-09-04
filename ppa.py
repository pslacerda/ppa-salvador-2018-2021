import csv
import sys
from popplerqt5 import Poppler
from PyQt5.QtCore import QRectF
from enum import Enum


class TipoPágina(Enum):
    AÇÕES_REGIONALIZADAS = 0
    DESCONHECIDO = 1


def descobreTipo(p):
    tl = p.textList()

    for i in range(len(tl)):
        if tl[i].text() == 'AÇÕES' and tl[i+1].text() == 'REGIONALIZADAS':
            return TipoPágina.AÇÕES_REGIONALIZADAS
    return TipoPágina.DESCONHECIDO


def extrairAções(p, p_num):
    tl = p.textList()

    if tl[0].text() == 'Salvador':
        desvio = 0
        if tl[4].text() == 'Continuação':
            eixo_r = tl[9].boundingBox()
        else:
            eixo_r = tl[8].boundingBox()
    else:
        desvio = 28.35299
        if tl[0].text() == 'Continuação':
            eixo_r = tl[5].boundingBox()
        else:
            eixo_r = tl[4].boundingBox()

    eixo_r = QRectF(eixo_r.left(), eixo_r.top(), 10000, eixo_r.bottom()-eixo_r.top())
    eixo = p.text(eixo_r)

    programa_r = QRectF(eixo_r.left(), eixo_r.bottom(), 382, eixo_r.bottom()-eixo_r.top())
    programa = p.text(programa_r)

    orçamento_r = QRectF(eixo_r.left()+382, eixo_r.bottom(), 144, eixo_r.bottom()-eixo_r.top())
    orçamento = p.text(orçamento_r)

    extra_r = QRectF(eixo_r.left()+382+144, eixo_r.bottom(), 10000, eixo_r.bottom()-eixo_r.top())
    extra = p.text(extra_r)

    ação_cabe_tb, meta_cabe_tb = None, None
    for i in range(len(tl)):
        if tl[i].text() == 'AÇÃO':
            ação_cabe_tb = tl[i].boundingBox()
            continue
        if 'META' in tl[i].text():
            meta_cabe_tb = tl[i].boundingBox()
            break
    else:
        print("Página %d inválida sem cabeçalho!" % p_num, file=sys.stderr)
        meta_cabe_tb = extra_r
        ação_cabe_tb = QRectF(programa_r.bottom(), programa_r.top(), programa_r.right(), programa_r.bottom())

    objetivo_r = QRectF(eixo_r.left(), programa_r.bottom(), 10000, ação_cabe_tb.top()-programa_r.bottom())
    objetivo = p.text(objetivo_r)
    if 'OBJETIVO:' not in objetivo:
        objetivo = ''

    linhas = []
    for t in tl:
        tb = t.boundingBox()
        if tb.left() > desvio+700 and tb.top() >= meta_cabe_tb.bottom():
            acima = meta_cabe_tb.bottom()
            if len(linhas) != 0:
                acima = tb.top()
            altura = tb.bottom()-acima
            if 'Continua' in t.text() or '|' in t.text():
                break
            linhas.append((acima, altura, tb))

    ações = []
    for acima, altura, meta_r in linhas:
        ação_r = QRectF(desvio+0, acima, 339, altura)
        ação = p.text(ação_r)

        produto_r = QRectF(desvio+339, acima, 150, altura)
        produto = p.text(produto_r)

        unidade_r = QRectF(desvio+339+150, acima, 90, altura)
        unidade = p.text(unidade_r)

        prefeitura_r = QRectF(desvio+339+150+90, acima, 110, altura)
        prefeitura = p.text(prefeitura_r)

        meta = p.text(meta_r)

        ações.append({
            'ação': ação,
            'produto': produto,
            'unidade': unidade,
            'prefeitura bairro': prefeitura,
            'meta física': meta
        })
    if ':' not in extra:
        print("Página %d inválida sem ':' no campo EXTRAORÇAMENTÁRIO" % p_num, file=sys.stderr)

    return {
        'eixo': eixo.replace('EIXO:', ''),
        'programa': programa.replace('PROGRAMA:', ''),
        'orçamentário': orçamento.replace('ORÇAMENTÁRIO', '').replace(':', ''),
        'extraorçamentário': extra.replace('EXTRAORÇAMENTÁRIO', '').replace(':', ''),
        'objetivo': objetivo.replace('OBJETIVO:', ''),
        'ações': ações
    }


def normalizar_resultado(res):
    def limpar_texto(t):
        return ' '.join(t.split())

    def texto_para_int(t):
        return int(limpar_texto(t.replace('.', '')))

    ppa = {}
    for item in res:
        eixo_nome = limpar_texto(item['eixo'])
        programa_nome = limpar_texto(item['programa'])
        extraorçamentário_novo = texto_para_int(item['extraorçamentário'])
        orçamentário_novo = texto_para_int(item['orçamentário'])
        objetivo = limpar_texto(item['objetivo'])

        eixo = ppa[eixo_nome] = ppa.get(eixo_nome, {})
        programa = eixo[programa_nome] = eixo.get(programa_nome, {})
        ações = programa['ações'] = programa.get('ações', [])

        if 'extraorçamentário' in programa and programa['extraorçamentário'] != extraorçamentário_novo:
            raise "Valor extraorçamentário alterado em EIXO:%s, PROGRAMA:%s" % (eixo_nome, programa_nome)
        if 'orçamentário' in programa and programa['orçamentário'] != orçamentário_novo:
            raise "Valor orçamentário alterado em EIXO:%s, PROGRAMA:%s" % (eixo_nome, programa_nome)

        if 'objetivo' not in programa:
            programa['objetivo'] = objetivo

        programa['extraorçamentário'] = extraorçamentário_novo
        programa['orçamentário'] = orçamentário_novo

        for ação in item['ações']:
            ações.append({
                'ação': limpar_texto(ação['ação']) or ações[-1]['ação'],
                'produto': limpar_texto(ação['produto'] or ações[-1]['produto']),
                'unidade': limpar_texto(ação['unidade']) or ações[-1]['unidade'],
                'prefeitura bairro': limpar_texto(ação['prefeitura bairro']) or ações[-1]['prefeitura bairro'],
                'meta física': texto_para_int(ação['meta física']) or ações[-1]['meta física']
            })
    return ppa


def main():
    arquivo_pdf = sys.argv[1]
    doc = Poppler.Document.load(arquivo_pdf)

    ações = []
    for p_num in range(doc.numPages()):
        página = doc.page(p_num)
        tipo = descobreTipo(página)
        if tipo == TipoPágina.AÇÕES_REGIONALIZADAS:
            ações.append(extrairAções(doc.page(p_num), p_num))

    ppa = normalizar_resultado(ações)

    arquivo_csv = sys.argv[2]
    with open(arquivo_csv, 'w') as arquivo_csv:
        escrever_cabeçalho = True
        for eixo_nome, eixo in ppa.items():
            for programa_nome, programa in eixo.items():
                for ação in programa['ações']:
                    ação.update(dict(
                        extra = programa['extraorçamentário'],
                        orçamentário = programa['orçamentário'],
                        objetivo = programa['objetivo'],
                        programa = programa_nome,
                        eixo = eixo_nome
                    ))
                    if escrever_cabeçalho:
                        campos = list(ação.keys())
                        escritor_csv = csv.DictWriter(arquivo_csv, campos)
                        escritor_csv.writeheader()
                        escrever_cabeçalho = False
                    else:
                        escritor_csv.writerow(ação)


if __name__ == '__main__':
    main()