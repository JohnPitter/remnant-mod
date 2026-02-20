"""
build_pak.py — Gera um PAK v8 do UE4 com MaxPlayers customizado, fix de rede,
e DataTable Stats_Scaling_NumPlayers modificada para 5-6 jogadores.

Uso:
    python build_pak.py [--players N] [--input FILE] [--output FILE]

Exemplos:
    python build_pak.py --players 6
    python build_pak.py --players 8 --input 4player.pak --output 8player.pak
"""

import zlib, struct, hashlib, argparse, re, sys, os


# Base do jogo original: 3 jogadores.
_BASE_PLAYERS = 3

# Diretorio com assets modificados (gerados por rebuild_scaling.py)
_MODIFIED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modified")


def network_settings(players):
    """Gera configuracoes de rede para o numero de jogadores.

    Configura SteamNetDriver (driver real do Remnant via Steam P2P),
    IpNetDriver (fallback/heranca), Player e GameNetworkManager.

    CVars do engine sao setadas em runtime pelo mod NetOptimize (UE4SS).
    """
    initial_timeout = 60.0 + 10.0 * players
    conn_timeout = 60.0 + 5.0 * players
    total_bandwidth = 200000 * players

    return f"""
[/Script/OnlineSubsystemSteam.SteamNetDriver]
NetServerMaxTickRate=60
LanServerMaxTickRate=60
MaxClientRate=200000
MaxInternetClientRate=200000
InitialConnectTimeout={initial_timeout:.1f}
ConnectionTimeout={conn_timeout:.1f}

[/Script/OnlineSubsystemUtils.IpNetDriver]
NetServerMaxTickRate=60
LanServerMaxTickRate=60
MaxClientRate=200000
MaxInternetClientRate=200000
InitialConnectTimeout={initial_timeout:.1f}
ConnectionTimeout={conn_timeout:.1f}

[/Script/Engine.Player]
ConfiguredInternetSpeed=200000
ConfiguredLanSpeed=200000

[/Script/Engine.GameNetworkManager]
TotalNetBandwidth={total_bandwidth}
MaxDynamicBandwidth=200000
MinDynamicBandwidth=40000
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
# Leitura de PAK v3 (legado, para ler o 4player.pak existente)
# ---------------------------------------------------------------------------

def read_pak_v3(filepath):
    """Extrai o conteudo INI de um PAK v3 (single-file legado)."""
    with open(filepath, 'rb') as f:
        data = f.read()

    block_start = struct.unpack_from('<q', data, 52)[0]
    block_end = struct.unpack_from('<q', data, 60)[0]
    compressed = data[block_start:block_end]
    return zlib.decompress(compressed).decode('utf-8')


# ---------------------------------------------------------------------------
# Construcao de PAK v8 (compativel com o formato do jogo)
# ---------------------------------------------------------------------------

# PAK v8 entry record: 70 bytes (compressed) or 53 bytes (uncompressed)
# Layout:
#   int64  data_offset          (offset absoluto no PAK)
#   int64  compressed_size
#   int64  uncompressed_size
#   uint8  compression_method   (0=none, 1=zlib)
#   byte[20] sha1               (hash do conteudo descomprimido)
#   -- if compressed:
#   int32  num_blocks
#   int64  block_start          (relativo ao data_offset)
#   int64  block_end            (relativo ao data_offset)
#   -- end if
#   uint8  encrypted            (0=false)
#   int32  block_size           (uncompressed_size para single block)

_V8_ENTRY_SIZE = 70  # for compressed single-block entries


def build_entry_record_v8(data_offset, compressed_size, uncompressed_size, sha1):
    """Constroi entry record de 70 bytes (PAK v8, zlib, single block)."""
    header_overhead = _V8_ENTRY_SIZE
    rec = struct.pack('<q', data_offset)
    rec += struct.pack('<q', compressed_size)
    rec += struct.pack('<q', uncompressed_size)
    rec += struct.pack('<B', 1)                                              # zlib (uint8)
    rec += sha1                                                              # 20 bytes
    rec += struct.pack('<i', 1)                                              # 1 block
    rec += struct.pack('<q', header_overhead)                                # block start (relative)
    rec += struct.pack('<q', header_overhead + compressed_size)              # block end (relative)
    rec += struct.pack('<B', 0)                                              # not encrypted
    rec += struct.pack('<i', uncompressed_size)                              # block size = uncomp size
    return rec


def build_index_v8(file_entries):
    """Constroi o indice do PAK v8 para multiplos arquivos.

    file_entries: lista de (filename, entry_record_bytes)
    """
    mount = b'../../../\x00'
    idx = struct.pack('<i', len(mount)) + mount
    idx += struct.pack('<i', len(file_entries))
    for filename, entry_rec in file_entries:
        fname = (filename + '\x00').encode('utf-8')
        idx += struct.pack('<i', len(fname)) + fname
        idx += entry_rec
    return idx


def build_footer_v8(index_offset, index_bytes):
    """Constroi o footer de 172 bytes (PAK v8).

    Layout:
      byte[16] encryption_key_guid  (zeros = no encryption)
      uint8    encrypted_index      (0)
      uint32   magic                (0x5A6F12E1)
      uint32   version              (8)
      int64    index_offset
      int64    index_size
      byte[20] index_sha1
      int32    num_compression_methods (1)
      byte[32] compression_method_name ("Zlib" + null padding)
      byte[32*3] reserved_methods   (zeros, 4 slots total)
    """
    ftr = struct.pack('<I', 0x5A6F12E1)                       # magic
    ftr += struct.pack('<I', 8)                              # version 8
    ftr += struct.pack('<q', index_offset)
    ftr += struct.pack('<q', len(index_bytes))
    ftr += hashlib.sha1(index_bytes).digest()                # 20 bytes

    # Compression method names (v8): 4 slots of 32 bytes each
    zlib_name = b'Zlib' + b'\x00' * 28                      # 32 bytes
    ftr += zlib_name
    ftr += b'\x00' * 32 * 3                                  # 3 empty slots

    assert len(ftr) == 172, f"Footer size mismatch: {len(ftr)} != 172"
    return ftr


def build_pak_v8(files):
    """Monta o PAK v8 com multiplos arquivos.

    files: lista de (pak_path, raw_bytes)
    Retorna bytes do PAK completo.
    """
    data_section = bytearray()
    file_entries = []

    for filename, raw_bytes in files:
        compressed = zlib.compress(raw_bytes)
        sha1 = hashlib.sha1(raw_bytes).digest()

        file_offset = len(data_section)
        entry_rec = build_entry_record_v8(
            file_offset, len(compressed), len(raw_bytes), sha1
        )
        data_section += entry_rec + compressed
        file_entries.append((filename, entry_rec))

    index = build_index_v8(file_entries)
    index_offset = len(data_section)
    footer = build_footer_v8(index_offset, index)

    return bytes(data_section) + index + footer


def main():
    parser = argparse.ArgumentParser(description='Gera mod PAK para Remnant')
    parser.add_argument('--players', type=int, default=6,
                        help='Numero maximo de jogadores (padrao: 6)')
    parser.add_argument('--input', default='4player.pak',
                        help='PAK de entrada com INI base (padrao: 4player.pak)')
    parser.add_argument('--output', default=None,
                        help='PAK de saida (padrao: {N}player.pak)')
    parser.add_argument('--no-scaling', action='store_true',
                        help='Nao incluir DataTable de scaling modificada')
    args = parser.parse_args()

    if args.output is None:
        args.output = f'{args.players}player.pak'

    # --- 1. Preparar INI ---
    ini_text = read_pak_v3(args.input)

    match = re.search(r'MaxPlayers=\d+', ini_text)
    if not match:
        print('ERRO: MaxPlayers nao encontrado no INI', file=sys.stderr)
        sys.exit(1)

    old_value = match.group()
    new_value = f'MaxPlayers={args.players}'
    new_ini = ini_text.replace(old_value, new_value)

    print(f'{old_value} -> {new_value}')

    # Injeta configuracoes de rede se ainda nao existem
    net_sections = [
        '[/Script/OnlineSubsystemSteam.SteamNetDriver]',
        '[/Script/OnlineSubsystemUtils.IpNetDriver]',
        '[/Script/Engine.Player]',
        '[/Script/Engine.GameNetworkManager]',
    ]
    missing = [s for s in net_sections if s not in new_ini]
    if missing:
        net_cfg = network_settings(args.players)
        new_ini = new_ini.rstrip() + '\n' + net_cfg.strip() + '\n'
        print(f'Rede injetada para {args.players} jogadores')

    # --- 2. Montar lista de arquivos ---
    files = [('Remnant/Config/DefaultGame.ini', new_ini.encode('utf-8'))]

    # --- 3. Adicionar DataTable de scaling se disponivel ---
    if not args.no_scaling:
        scaling_dir = os.path.join(_MODIFIED_DIR, "Remnant", "Content", "_Core", "Stats")
        uasset_path = os.path.join(scaling_dir, "Stats_Scaling_NumPlayers.uasset")
        uexp_path = os.path.join(scaling_dir, "Stats_Scaling_NumPlayers.uexp")

        if os.path.exists(uasset_path) and os.path.exists(uexp_path):
            with open(uasset_path, 'rb') as f:
                files.append((
                    'Remnant/Content/_Core/Stats/Stats_Scaling_NumPlayers.uasset',
                    f.read()
                ))
            with open(uexp_path, 'rb') as f:
                files.append((
                    'Remnant/Content/_Core/Stats/Stats_Scaling_NumPlayers.uexp',
                    f.read()
                ))
            print('DataTable Stats_Scaling_NumPlayers incluida (rows 1-6)')
        else:
            print(f'AVISO: DataTable nao encontrada em {scaling_dir}')
            print('       Execute rebuild_scaling.py primeiro para gerar os arquivos.')

    # --- 4. Construir PAK v8 ---
    pak_data = build_pak_v8(files)

    with open(args.output, 'wb') as f:
        f.write(pak_data)

    print(f'OK: {args.output} ({len(pak_data)} bytes, {len(files)} arquivo(s), PAK v8)')


if __name__ == '__main__':
    main()
