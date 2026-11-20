"""Gera setores.js (guia de critérios) a partir dos textos da pasta 'setores'.

Uso:  python gera_guia.py  [pasta_setores]  [pasta_saida]
"""
import json, os, re, sys

SRC = r'C:\Users\MATEUS\Desktop\Patentes\setores'
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    SRC = sys.argv[1]
if len(sys.argv) > 2:
    OUT_DIR = sys.argv[2]

# Grupos de setores (divisões CNAE 2.0, que é o que a coluna ISIC da base traz)
GRUPOS = [
    {'chave': '10, 11 e 12', 'nome': 'Alimentos, bebidas e fumo',
     'divisoes': ['10', '11', '12']},
    {'chave': '13, 171, 172, 18, 58, 592', 'nome': 'Têxteis, celulose e papel, impressão e edição',
     'divisoes': ['13', '17.1', '17.2', '18', '58', '59.2']},
    {'chave': '14, 15, 16, 173, 174, 31, 32',
     'nome': 'Vestuário e acessórios; couro, artefatos de couro e calçados; produtos de madeira; embalagens e artefatos de papel; móveis; indústrias diversas',
     'divisoes': ['14', '15', '16', '17.3', '17.4', '31', '32']},
    {'chave': '19, 20, 21 e 22',
     'nome': 'Derivados de petróleo e biocombustíveis; químicos; farmoquímicos e farmacêuticos; borracha e plástico',
     'divisoes': ['19', '20', '21', '22']},
    {'chave': '23, 24', 'nome': 'Minerais não-metálicos e metalurgia',
     'divisoes': ['23', '24']},
    {'chave': '25, 28, 29, 30',
     'nome': 'Produtos de metal; máquinas e equipamentos; veículos automotores; outros equipamentos de transporte',
     'divisoes': ['25', '28', '29', '30']},
    {'chave': '26, 27',
     'nome': 'Equipamentos de informática, produtos eletrônicos e ópticos; máquinas, aparelhos e materiais elétricos',
     'divisoes': ['26', '27']},
]


def ler(nome_base):
    for ext in ('.csv', '.txt'):
        p = os.path.join(SRC, nome_base + ext)
        if os.path.exists(p):
            with open(p, encoding='utf-8-sig') as f:
                return f.read()
    raise FileNotFoundError(nome_base)


def limpar(t):
    t = t.replace('\ufeff', '').replace('\xa0', ' ')
    # títulos colados no texto, ex.: "Processo_Equipamentos de informática ... – 26, 27"
    t = re.sub(r'(?:Processo|Produto)_[^–\n]*–\s*[\d,\s]+', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    # números de página soltos ("; 40 - Melhoria", ". 12 13 Métodos")
    t = re.sub(r'(?<=[;.]) \d{2} -(?= )', ' ', t)
    t = re.sub(r'(?<=\.) 12 13(?= )', '', t)
    # marcadores de lista perdidos: "- - - - -", "; - Melhoria", "; e - Novos"
    t = re.sub(r'(?:\s*-(?=\s)){2,}', ' ', t)
    t = re.sub(r'(?<=[;.])\s+(e\s+)?-\s+', lambda m: ' ' + (m.group(1) or ''), t)
    t = re.sub(r';\s*\.', ';', t)
    t = re.sub(r';\s*;', ';', t)
    t = re.sub(r'\s+([;,.)])', r'\1', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def itens(t):
    """Divide nos ';' que separam critérios (fora de parênteses)."""
    partes, buf, prof = [], '', 0
    for i, c in enumerate(t):
        if c == '(':
            prof += 1
        elif c == ')':
            prof = max(0, prof - 1)
        # ';' fora de parênteses, ou parêntese nunca fechado seguido de novo critério
        resto = t[i + 1:].lstrip()
        novo_item = (c == ';' and resto[:1].isupper()
                     and re.match(r'(Introdu|Incorpora|Aperfei|Melhori|Moderniz|Automatiz|Utiliza|Sofistica|Adequa|Explora|Avanço|Diversifica|Deslocamento|Novos?|Amplia|Atualiza|Inova)', resto))
        if c == ';' and (prof == 0 or novo_item):
            partes.append(buf)
            buf, prof = '', 0
        else:
            buf += c
    partes.append(buf)
    out = []
    for p in partes:
        p = re.sub(r'^\s*(?:e\s+)', '', p.strip()).strip()
        p = p.rstrip(' ;.').strip()
        if len(p) < 15:
            continue
        p = p[0].upper() + p[1:]
        if p.count('(') > p.count(')'):
            p += ')'
        out.append(p + '.')
    return out


def main():
    guia = {
        'geral': {
            'processo': limpar(ler('Processo_Geral')),
            'produto': limpar(ler('Produto_Geral')),
        },
        'grupos': [],
    }
    for g in GRUPOS:
        guia['grupos'].append({
            **g,
            'processo': itens(limpar(ler('Processo ' + g['chave']))),
            'produto': itens(limpar(ler('Produto ' + g['chave']))),
        })
    data = json.dumps(guia, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, 'setores.js'), 'w', encoding='utf-8') as f:
        f.write('window.SETORES = ' + data + ';\n')
    print('OK: setores.js gerado com', len(guia['grupos']), 'grupos')


if __name__ == '__main__':
    main()
