"""Extrai as primeiras 250 patentes do CSV e gera patentes250.json + patentes250.js
(o .js permite abrir o index.html direto com duplo clique, sem servidor).

Limpeza aplicada ao título e ao resumo:
  - leitura correta em UTF-8 (o arquivo é UTF-8 com BOM)
  - entidades HTML (&#34; &#39; &amp;nbsp; ...)
  - mojibake de dupla codificação (ex.: "mã©todo", "â\x80\x9c")
  - caracteres de controle do Windows-1252 (\x93 \x94 -> aspas)
  - lixo de BOM UTF-16 ("ÿþ"), hífens invisíveis, espaços e quebras de linha
  - cabeçalhos de formulário no início ("1 / 1 resumo", "resumo patente de invenção:")
"""
import csv, html, json, re, sys, os

SRC = r'C:\Users\MATEUS\Desktop\Patentes\resultado_classificado_geral.csv'
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
N = 250

if len(sys.argv) > 1:
    SRC = sys.argv[1]
if len(sys.argv) > 2:
    OUT_DIR = sys.argv[2]

csv.field_size_limit(2**31 - 1)

# Sequência UTF-8 lida como latin-1 e depois passada para minúsculas:
# o byte inicial 0xC3 (Ã) virou "ã", 0xC2 (Â) virou "â" etc.
MOJI = re.compile(r'[ãâ][\x80-\xbf](?:[\x80-\xbf])?|[ÃÂ][\x80-\xbf]')
MOJI_HINT = re.compile(r'[ãâÃÂ][\x80-\xbf©§£ºª³µ¡¢]')


def _fix_seq(m):
    s = m.group(0)
    lead = {'ã': 0xC3, 'â': 0xE2, 'Ã': 0xC3, 'Â': 0xC2}[s[0]]
    if lead == 0xE2 and s[0] == 'â' and len(s) == 2:
        lead = 0xC2  # "Â" minúsculo + 1 byte
    b = bytes([lead] + [ord(c) for c in s[1:]])
    try:
        return b.decode('utf-8')
    except UnicodeDecodeError:
        if len(s) == 3:  # talvez só os 2 primeiros formem o caractere
            try:
                return bytes([0xC3 if s[0] in 'ãÃ' else lead, ord(s[1])]).decode('utf-8') + s[2]
            except UnicodeDecodeError:
                pass
        return s


def fix_mojibake(s):
    if not MOJI_HINT.search(s):
        return s
    # Primeiro tenta a reversão clássica (texto não foi alterado após o erro)
    try:
        t = s.encode('cp1252', errors='strict').decode('utf-8')
        return t
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    # Caso geral: troca sequência por sequência
    t = MOJI.sub(_fix_seq, s)
    # bytes de continuação que viraram caracteres latin-1 visíveis (ex.: "ã©" -> é)
    t = re.sub(r'ã([\xa0-\xbf])', lambda m: bytes([0xC3, ord(m.group(1))]).decode('utf-8'), t)
    # o texto original estava em minúsculas: devolve maiúsculas acentuadas ao normal
    t = re.sub(r'(?<=[a-zà-ÿ])[ÀÁÂÃÉÊÍÓÔÕÚÇ]', lambda m: m.group(0).lower(), t)
    t = re.sub(r'[ÀÁÂÃÉÊÍÓÔÕÚÇ](?=[a-zà-ÿ])', lambda m: m.group(0).lower(), t)
    return t


CP1252 = {i: bytes([i]).decode('cp1252', errors='ignore') or '' for i in range(0x80, 0xA0)}


def fix_c1(s):
    return ''.join(CP1252.get(ord(c), c) if 0x80 <= ord(c) < 0xA0 else c for c in s)


PREFIX = re.compile(
    r'^\s*(?:\d+\s*/\s*\d+\s*)?'
    r'(?:texto\s+do\s+resumo\s*)?'
    r'(?:(?:resumo|abstract)(?:\s+da)?(?:\s+patente\s+de\s+inven[çc][ãa]o)?(?:\s+para)?\s*:?\s*)*',
    re.I)


def clean(s, is_abstract=False):
    s = s or ''
    for _ in range(3):  # entidades aninhadas (&amp;nbsp;)
        u = html.unescape(s)
        if u == s:
            break
        s = u
    s = s.replace('\ufeff', '')
    if s.startswith(('ÿþ', 'þÿ')):
        s = s[2:]
    s = fix_mojibake(s)
    s = fix_c1(s)
    s = s.replace('\xad', '').replace('\xa0', ' ').replace('\ufffd', '')
    s = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = s.replace('ß', 'β')  # em português "ß" só aparece como beta mal codificado
    if is_abstract:
        s = PREFIX.sub('', s, count=1).strip()
        letters = [c for c in s if c.isalpha()]
        if letters and sum(c.isupper() for c in letters) / len(letters) < 0.02:
            # texto todo em minúsculas na base: devolve maiúscula no início das frases
            s = re.sub(r'([.!?][”"]?\s+|[”]\s+|^[“"]?)([a-zà-ÿ])',
                       lambda m: m.group(1) + m.group(2).upper(), s)
    if s and s[0].islower():
        s = s[0].upper() + s[1:]
    return s


def main():
    rows = []
    with open(SRC, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f, delimiter=';')
        for i, row in enumerate(reader):
            if i >= N:
                break
            title = clean(row.get('title'))
            abstract = clean(row.get('abstract'), is_abstract=True)
            if len(abstract) < 25:
                abstract = ''
            rows.append({
                'uid': i + 1,
                'id': (row.get('publication_number') or '').strip(),
                'filing_date': (row.get('filing_date') or '').strip(),
                'title': title,
                'abstract': abstract,
                'ipc': (row.get('ipc_codes') or '').strip(),
                'ipc4': (row.get('4-digitos IPC') or '').strip(),
                'isic': (row.get('ISIC') or '').strip(),
                'sim_processo': float(row.get('sim_processo') or 0),
                'sim_produto': float(row.get('sim_produto') or 0),
                'diferenca': float(row.get('diferenca') or 0),
                'auto_class': (row.get('classificacao') or '').strip(),
            })

    data = json.dumps(rows, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, 'patentes250.json'), 'w', encoding='utf-8') as f:
        f.write(data)
    with open(os.path.join(OUT_DIR, 'patentes250.js'), 'w', encoding='utf-8') as f:
        f.write('window.PATENTES = ' + data + ';\n')
    print(f'OK: {len(rows)} patentes exportadas para {OUT_DIR}')
    vazios = [r['uid'] for r in rows if not r['abstract']]
    if vazios:
        print('Sem resumo legível na base:', vazios)


if __name__ == '__main__':
    main()
