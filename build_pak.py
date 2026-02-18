"""
build_pak.py — Gera um PAK v3 do UE4 com MaxPlayers customizado.

Uso:
    python build_pak.py [--players N] [--input FILE] [--output FILE]

Exemplos:
    python build_pak.py --players 6
    python build_pak.py --players 8 --input 4player.pak --output 8player.pak
"""

import zlib, struct, hashlib, argparse, re, sys


def read_pak(filepath):
    """Extrai o conteudo INI de um PAK v3."""
    with open(filepath, 'rb') as f:
        data = f.read()

    block_start = struct.unpack_from('<q', data, 52)[0]
    block_end = struct.unpack_from('<q', data, 60)[0]
    compressed = data[block_start:block_end]
    return zlib.decompress(compressed).decode('utf-8')


def build_entry_record(compressed_size, uncompressed_size, sha1, header_size=73):
    """Constroi o entry record de 73 bytes."""
    rec = struct.pack('<q', 0)                          # offset
    rec += struct.pack('<q', compressed_size)
    rec += struct.pack('<q', uncompressed_size)
    rec += struct.pack('<i', 1)                         # zlib
    rec += sha1                                         # 20 bytes
    rec += struct.pack('<i', 1)                         # 1 bloco
    rec += struct.pack('<q', header_size)                # block start
    rec += struct.pack('<q', header_size + compressed_size)  # block end
    rec += struct.pack('<B', 0)                         # nao encriptado
    rec += struct.pack('<i', 65536)                     # block size
    return rec


def build_index(entry_record):
    """Constroi o indice do PAK."""
    mount = b'../../../\x00'
    fname = b'Remnant/Config/DefaultGame.ini\x00'

    idx = struct.pack('<i', len(mount)) + mount
    idx += struct.pack('<i', 1)                         # 1 entrada
    idx += struct.pack('<i', len(fname)) + fname
    idx += entry_record
    return idx


def build_footer(index_offset, index_bytes):
    """Constroi o footer de 44 bytes."""
    ftr = struct.pack('<I', 0x5A6F12E1)                 # magic
    ftr += struct.pack('<I', 3)                         # versao
    ftr += struct.pack('<q', index_offset)
    ftr += struct.pack('<q', len(index_bytes))
    ftr += hashlib.sha1(index_bytes).digest()
    return ftr


def build_pak(ini_text):
    """Monta o PAK completo a partir do texto INI."""
    ini_bytes = ini_text.encode('utf-8')
    compressed = zlib.compress(ini_bytes)
    sha1 = hashlib.sha1(ini_bytes).digest()

    entry_rec = build_entry_record(len(compressed), len(ini_bytes), sha1)
    index = build_index(entry_rec)
    index_offset = len(entry_rec) + len(compressed)
    footer = build_footer(index_offset, index)

    return entry_rec + compressed + index + footer


def main():
    parser = argparse.ArgumentParser(description='Gera mod PAK para Remnant')
    parser.add_argument('--players', type=int, default=6,
                        help='Numero maximo de jogadores (padrao: 6)')
    parser.add_argument('--input', default='4player.pak',
                        help='PAK de entrada (padrao: 4player.pak)')
    parser.add_argument('--output', default=None,
                        help='PAK de saida (padrao: {N}player.pak)')
    args = parser.parse_args()

    if args.output is None:
        args.output = f'{args.players}player.pak'

    ini_text = read_pak(args.input)

    match = re.search(r'MaxPlayers=\d+', ini_text)
    if not match:
        print('ERRO: MaxPlayers nao encontrado no INI', file=sys.stderr)
        sys.exit(1)

    old_value = match.group()
    new_value = f'MaxPlayers={args.players}'
    new_ini = ini_text.replace(old_value, new_value)

    print(f'{old_value} -> {new_value}')

    pak_data = build_pak(new_ini)
    with open(args.output, 'wb') as f:
        f.write(pak_data)

    verify_text = read_pak(args.output)
    if new_value in verify_text:
        print(f'OK: {args.output} ({len(pak_data)} bytes)')
    else:
        print('ERRO: verificacao falhou', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
