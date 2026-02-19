"""
build_pak.py — Gera um PAK v3 do UE4 com MaxPlayers customizado e fix de rede.

Uso:
    python build_pak.py [--players N] [--input FILE] [--output FILE]

Exemplos:
    python build_pak.py --players 6
    python build_pak.py --players 8 --input 4player.pak --output 8player.pak
"""

import zlib, struct, hashlib, argparse, re, sys


# Base do jogo original: 3 jogadores.
_BASE_PLAYERS = 3


def network_settings(players):
    """Gera configuracoes de rede escaladas para o numero de jogadores.

    Valores escalam a partir do baseline de 3 jogadores. Com 3 ou menos,
    usa defaults do UE4 (nenhuma secao injetada). Acima de 3, escala
    bandwidth, timeouts e replicacao proporcionalmente.
    """
    scale = players / _BASE_PLAYERS  # 6 players = 2.0x, 8 = 2.67x, etc.

    # Banda por cliente: 15000 default * escala, cap 150000
    client_rate = min(int(15000 * scale), 150000)

    # Banda total do servidor: 100000 por jogador
    total_bandwidth = 100000 * players

    # Timeouts: base 30s, escalam com mais jogadores
    initial_timeout = 30.0 + 15.0 * (players - _BASE_PLAYERS)
    conn_timeout = 30.0 + 10.0 * (players - _BASE_PLAYERS)

    # Velocidade reportada pelo cliente: acompanha client_rate
    internet_speed = client_rate

    # Intervalo de envio de movimento: mais jogadores = mais frequente
    # Default ~18Hz (0.0555), escala ate ~60Hz (0.0166)
    move_delta = max(0.0555 / scale, 0.0111)
    move_delta_throttled = max(0.0666 / scale, 0.0166)

    # Tolerancia de posicao: mais jogadores = mais permissivo
    pos_error_sq = 3.0 * scale

    # Throttle de movimento: aplica a partir de quantos jogadores
    throttle_over = max(players - 1, _BASE_PLAYERS)

    # Deteccao de discrepancia de tempo: desativa com mais de 3
    time_discrepancy = 'true' if players <= _BASE_PLAYERS else 'false'

    return f"""
[/Script/OnlineSubsystemUtils.IpNetDriver]
MaxClientRate={client_rate}
MaxInternetClientRate={client_rate}
InitialConnectTimeout={initial_timeout:.1f}
ConnectionTimeout={conn_timeout:.1f}

[/Script/Engine.Player]
ConfiguredInternetSpeed={internet_speed}
ConfiguredLanSpeed={internet_speed}

[/Script/Engine.GameNetworkManager]
TotalNetBandwidth={total_bandwidth}
MaxDynamicBandwidth={client_rate}
MinDynamicBandwidth=10000
MoveRepSize=42.0
MAXPOSITIONERRORSQUARED={pos_error_sq:.1f}
CLIENTADJUSTUPDATECOST=180.0
MAXCLIENTUPDATEINTERVAL=0.25
MaxMoveDeltaTime=0.125
ClientNetSendMoveDeltaTime={move_delta:.4f}
ClientNetSendMoveDeltaTimeThrottled={move_delta_throttled:.4f}
ClientNetSendMoveThrottleAtNetSpeed=10000
ClientNetSendMoveThrottleOverPlayerCount={throttle_over}
bMovementTimeDiscrepancyDetection={time_discrepancy}
"""


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

    # Injeta configuracoes de rede escaladas para o numero de jogadores
    net_sections = [
        '[/Script/OnlineSubsystemUtils.IpNetDriver]',
        '[/Script/Engine.Player]',
        '[/Script/Engine.GameNetworkManager]',
    ]
    missing = [s for s in net_sections if s not in new_ini]
    if missing:
        net_cfg = network_settings(args.players)
        new_ini = new_ini.rstrip() + '\n' + net_cfg.strip() + '\n'
        print(f'Rede escalada para {args.players} jogadores ({args.players}/{_BASE_PLAYERS} = {args.players/_BASE_PLAYERS:.2f}x)')

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
