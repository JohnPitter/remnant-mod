"""
build_pak.py — Gera PAKs v3 do UE4 para o mod de Remnant.

Gera dois PAKs:
  - {N}player.pak         (DefaultGame.ini: MaxPlayers + GameNetworkManager)
  - {N}player_engine.pak  (DefaultEngine.ini: SteamNetDriver + CVars)

Uso:
    python build_pak.py [--players N] [--input FILE] [--output FILE]

Exemplos:
    python build_pak.py --players 6
    python build_pak.py --players 8 --input 4player.pak --output 8player.pak
"""

import zlib, struct, hashlib, argparse, re, sys


# Base do jogo original: 3 jogadores.
_BASE_PLAYERS = 3


# ---------------------------------------------------------------------------
# Configuracoes de rede — DefaultGame.ini
# ---------------------------------------------------------------------------

def game_network_settings(players):
    """Settings que pertencem ao DefaultGame.ini (GameNetworkManager)."""
    total_bandwidth = 100000 * players

    return f"""
[/Script/Engine.GameNetworkManager]
TotalNetBandwidth={total_bandwidth}
MaxDynamicBandwidth=100000
MinDynamicBandwidth=20000
MoveRepSize=42.0
MAXPOSITIONERRORSQUARED=25.0
CLIENTADJUSTUPDATECOST=180.0
MAXCLIENTUPDATEINTERVAL=0.125
MaxMoveDeltaTime=0.125
ClientNetSendMoveDeltaTime=0.0166
ClientNetSendMoveDeltaTimeThrottled=0.0222
ClientNetSendMoveThrottleAtNetSpeed=10000
ClientNetSendMoveThrottleOverPlayerCount={max(players - 1, _BASE_PLAYERS)}
bMovementTimeDiscrepancyDetection=false
bUseDistanceBasedRelevancy=true
"""


# ---------------------------------------------------------------------------
# Configuracoes de rede — DefaultEngine.ini
# ---------------------------------------------------------------------------

def engine_network_settings(players):
    """Settings que pertencem ao DefaultEngine.ini.

    CRITICO: Remnant usa Steam P2P, entao o driver de rede real eh
    SteamNetDriver, nao IpNetDriver. Configurar apenas IpNetDriver
    pode ser ignorado pelo jogo. Aqui configuramos AMBOS os drivers
    + CVars do engine que so funcionam via DefaultEngine.ini.
    """
    initial_timeout = 60.0 + 10.0 * players
    conn_timeout = 60.0 + 5.0 * players

    # Bloco de settings identico para ambos os drivers
    driver_settings = f"""\
NetServerMaxTickRate=60
LanServerMaxTickRate=60
MaxClientRate=100000
MaxInternetClientRate=100000
InitialConnectTimeout={initial_timeout:.1f}
ConnectionTimeout={conn_timeout:.1f}"""

    return f"""
[/Script/OnlineSubsystemSteam.SteamNetDriver]
{driver_settings}

[/Script/OnlineSubsystemUtils.IpNetDriver]
{driver_settings}

[/Script/Engine.Player]
ConfiguredInternetSpeed=100000
ConfiguredLanSpeed=100000

[ConsoleVariables]
p.NetEnableListenServerSmoothing=1
p.NetClientSmoothingMode=2
p.NetEnableMoveCombining=1
p.NetCorrectionLifetime=0.5
p.NetServerMoveTimestampExpiredWarningThreshold=5.0
net.IpNetDriverMaxDesiredSendSize=4096
net.MaxRPCPerNetUpdate=8
net.AllowEncryption=0
"""


# ---------------------------------------------------------------------------
# Leitura / construcao de PAK v3
# ---------------------------------------------------------------------------

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


def build_index(entry_record, config_filename='DefaultGame.ini'):
    """Constroi o indice do PAK."""
    mount = b'../../../\x00'
    fname = f'Remnant/Config/{config_filename}\x00'.encode()

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


def build_pak(ini_text, config_filename='DefaultGame.ini'):
    """Monta o PAK completo a partir do texto INI."""
    ini_bytes = ini_text.encode('utf-8')
    compressed = zlib.compress(ini_bytes)
    sha1 = hashlib.sha1(ini_bytes).digest()

    entry_rec = build_entry_record(len(compressed), len(ini_bytes), sha1)
    index = build_index(entry_rec, config_filename)
    index_offset = len(entry_rec) + len(compressed)
    footer = build_footer(index_offset, index)

    return entry_rec + compressed + index + footer


def write_and_verify(pak_data, output_path, expected_text):
    """Escreve o PAK e verifica o conteudo."""
    with open(output_path, 'wb') as f:
        f.write(pak_data)

    verify = read_pak(output_path)
    if expected_text in verify:
        print(f'  OK: {output_path} ({len(pak_data)} bytes)')
        return True
    else:
        print(f'  ERRO: verificacao falhou para {output_path}', file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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

    # --- PAK 1: DefaultGame.ini (MaxPlayers + GameNetworkManager) ---
    print(f'[1/2] DefaultGame.ini')

    ini_text = read_pak(args.input)

    match = re.search(r'MaxPlayers=\d+', ini_text)
    if not match:
        print('ERRO: MaxPlayers nao encontrado no INI', file=sys.stderr)
        sys.exit(1)

    old_value = match.group()
    new_value = f'MaxPlayers={args.players}'
    new_ini = ini_text.replace(old_value, new_value)
    print(f'  {old_value} -> {new_value}')

    # Injeta GameNetworkManager se nao existe
    if '[/Script/Engine.GameNetworkManager]' not in new_ini:
        game_cfg = game_network_settings(args.players)
        new_ini = new_ini.rstrip() + '\n' + game_cfg.strip() + '\n'
        print(f'  GameNetworkManager injetado (TotalBandwidth={100000 * args.players})')

    # Remove settings de IpNetDriver e Player do DefaultGame.ini
    # (agora ficam no DefaultEngine.ini onde pertencem)
    for section in ['[/Script/OnlineSubsystemUtils.IpNetDriver]', '[/Script/Engine.Player]']:
        start = new_ini.find(section)
        if start != -1:
            next_section = new_ini.find('\n[', start + 1)
            if next_section == -1:
                next_section = len(new_ini)
            new_ini = new_ini[:start] + new_ini[next_section:]
            print(f'  Removido {section} (movido para DefaultEngine.ini)')

    pak1 = build_pak(new_ini, 'DefaultGame.ini')
    ok1 = write_and_verify(pak1, args.output, new_value)

    # --- PAK 2: DefaultEngine.ini (SteamNetDriver + IpNetDriver + CVars) ---
    print(f'[2/2] DefaultEngine.ini')

    engine_ini = engine_network_settings(args.players).strip() + '\n'
    engine_output = args.output.replace('.pak', '_engine.pak')

    pak2 = build_pak(engine_ini, 'DefaultEngine.ini')
    ok2 = write_and_verify(pak2, engine_output, 'SteamNetDriver')

    if ok1 and ok2:
        print(f'\nPronto! Copie AMBOS para ~mods:')
        print(f'  {args.output}')
        print(f'  {engine_output}')
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
