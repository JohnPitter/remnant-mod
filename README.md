# Remnant: From the Ashes — 6 Player Co-op Mod

Mod que aumenta o limite de jogadores em sessões co-op do **Remnant: From the Ashes** de 3 para **6 jogadores**, com otimizações de rede e balanceamento de inimigos.

Composto por três módulos:
- **PAK mod** — `DefaultGame.ini`: `MaxPlayers` + `SteamNetDriver` + `IpNetDriver` + `GameNetworkManager`
- **EnemyScaling (UE4SS)** — escala vida e dano dos inimigos com base no número de jogadores
- **NetOptimize (UE4SS)** — lobby override (força MaxPlayers no GameSession em runtime), smoothing, interpolação, CVars de rede e prioridades

## Instalação

### Download rápido

1. Baixe o arquivo **`6player.pak`** da página de [Releases](../../releases)
2. Localize a pasta de instalação do jogo:
   - **Steam:** clique com o botão direito no jogo > Gerenciar > Ver arquivos locais
   - Caminho típico: `C:\Program Files (x86)\Steam\steamapps\common\Remnant From the Ashes\`
3. Navegue até a pasta de PAKs:
   ```
   Remnant From the Ashes\Remnant\Content\Paks\
   ```
4. Crie uma pasta chamada **`~mods`** dentro de `Paks` (se ainda não existir)
5. Copie o arquivo `6player.pak` para dentro de `~mods`:
   ```
   Remnant From the Ashes\
   └── Remnant\
       └── Content\
           └── Paks\
               ├── ~mods\
               │   └── 6player.pak    ← aqui
               ├── Remnant-WindowsNoEditor.pak
               └── ...
   ```
6. Inicie o jogo normalmente

> **Importante:** O prefixo `~` no nome da pasta garante que o Unreal Engine carregue os mods **depois** dos arquivos originais, permitindo que o mod sobrescreva as configurações padrão.

### Instalação do EnemyScaling (balanceamento)

O mod de balanceamento usa [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) para escalar vida e dano dos inimigos em tempo de execução.

1. Baixe o **UE4SS** compatível com UE4 na página de [Releases do UE4SS](https://github.com/UE4SS-RE/RE-UE4SS/releases)
2. Extraia o conteúdo na pasta de binários do jogo:
   ```
   Remnant From the Ashes\Remnant\Binaries\Win64\
   ```
   Isso cria a pasta `Mods/` e os arquivos `xinput1_3.dll`, `UE4SS.dll`, etc.
3. Copie as pastas `ue4ss/Mods/EnemyScaling/` e `ue4ss/Mods/NetOptimize/` para dentro de `Mods/`:
   ```
   Remnant From the Ashes\
   └── Remnant\
       └── Binaries\
           └── Win64\
               ├── xinput1_3.dll         ← UE4SS
               ├── UE4SS.dll             ← UE4SS
               └── Mods\
                   ├── EnemyScaling\     ← balanceamento
                   │   ├── Scripts\main.lua
                   │   └── enabled.txt
                   └── NetOptimize\      ← smoothing e rede
                       ├── Scripts\main.lua
                       └── enabled.txt
   ```
4. Inicie o jogo. O console do UE4SS mostra logs `[EnemyScaling]` e `[NetOptimize]` confirmando que os mods estão ativos.

#### Configuração do EnemyScaling

Edite os valores no topo de `main.lua`:

| Variável | Padrão | Descrição |
|---|---|---|
| `HEALTH_PER_EXTRA` | `0.35` | +35% HP por jogador acima de 3 |
| `DAMAGE_PER_EXTRA` | `0.15` | +15% dano por jogador acima de 3 |
| `BASE_PLAYERS` | `3` | Jogadores que o jogo já escala nativamente |
| `SCAN_INTERVAL_MS` | `3000` | Intervalo de scan de inimigos (ms) |

Exemplo com 6 jogadores (3 extras): HP = 2.05x, Dano = 1.45x.

#### Configuração do NetOptimize

O NetOptimize resolve o limite de 3 jogadores no lobby Steam, elimina teleporte residual e melhora a fluidez visual.

**Lobby override** — O jogo cria o lobby Steam com `NumPublicConnections=3` hardcoded no código. O `MaxPlayers=6` no INI configura o engine, mas **não** altera o lobby. O NetOptimize força `MaxPlayers` no `GameSession` em runtime e hookeia `RegisterPlayer` para garantir que o engine aceite mais conexões.

| Variável | Padrão | Descrição |
|---|---|---|
| `MAX_PLAYERS` | `6` | Máximo de jogadores (força no lobby Steam em runtime) |
| `SMOOTH_LOCATION_TIME` | `0.100` | Tempo de interpolação de posição (s) |
| `LISTEN_SMOOTH_LOCATION_TIME` | `0.080` | Interpolação no listen server (s) |
| `MAX_SMOOTH_DISTANCE` | `512.0` | Distância máx para suavizar (além disso, snap) |
| `PLAYER_NET_PRIORITY` | `3.0` | Prioridade de rede dos jogadores (default UE4: 1.0) |
| `MIN_NET_UPDATE_FREQ` | `33.0` | Update mínimo de rede para jogadores (Hz) |

O mod também seta CVars do engine via console:

| CVar | Valor | Efeito |
|---|---|---|
| `p.NetEnableListenServerSmoothing` | `1` | Habilita smoothing no listen server (desabilitado por default!) |
| `p.NetClientSmoothingMode` | `2` | Interpolação exponencial (mais suave que linear) |
| `p.NetEnableMoveCombining` | `1` | Combina updates de movimento em pacotes maiores |
| `p.NetCorrectionLifetime` | `0.5` | Correções de posição são suavizadas em 0.5s em vez de snap |

### Desinstalação

- **PAK mod:** remova `6player.pak` da pasta `~mods`
- **Mods UE4SS:** delete as pastas `EnemyScaling` e/ou `NetOptimize` de dentro de `Mods/`, ou remova o `enabled.txt` de cada um

---

## Gerando um mod customizado

Se quiser um número diferente de jogadores, use o script `build_pak.py`:

```bash
# Requer Python 3 (sem dependências externas)
python build_pak.py --players 8
```

Opções:

| Flag        | Padrão         | Descrição                         |
|-------------|----------------|-----------------------------------|
| `--players` | `6`            | Número máximo de jogadores        |
| `--input`   | `4player.pak`  | PAK base para extrair o INI      |
| `--output`  | `{N}player.pak`| Nome do arquivo de saída          |

Exemplos:

```bash
python build_pak.py --players 4                           # volta para 4 jogadores
python build_pak.py --players 10 --output custom.pak      # 10 jogadores
```

---

## Otimizações de rede

O `build_pak.py` injeta todas as configurações de rede no `DefaultGame.ini`, incluindo `SteamNetDriver` (driver real do Remnant via Steam P2P) e `IpNetDriver` (fallback). CVars do engine são setadas em runtime pelo mod NetOptimize (UE4SS).

### PAK mod — Net drivers + GameNetworkManager

| Configuração | Padrão UE4 | Mod | Efeito |
|---|---|---|---|
| `SteamNetDriver.NetServerMaxTickRate` | 30 | **60** | Tick rate do servidor (Hz) |
| `SteamNetDriver.MaxClientRate` | 15,000 | **100,000** | Banda máxima por cliente (bytes/s) |
| `ConfiguredInternetSpeed` | 10,000 | **100,000** | Velocidade reportada pelo cliente |
| `TotalNetBandwidth` | 32,000 | **100K × N** | Banda total (600K para 6 players) |
| `MAXPOSITIONERRORSQUARED` | 3.0 | **25.0** | Tolerância de posição antes de corrigir |
| `ClientNetSendMoveDeltaTime` | 0.0555 | **0.0166** | Envio de movimento (~60Hz vs ~18Hz) |
| `MAXCLIENTUPDATEINTERVAL` | 0.25 | **0.125** | Intervalo máximo de update do servidor |
| `bMovementTimeDiscrepancyDetection` | true | **false** | Desativa kick por discrepância |
| `bUseDistanceBasedRelevancy` | false | **true** | Atores distantes atualizam menos — poupa banda |

### NetOptimize — Lobby override + CVars em runtime

| Configuração | Padrão | Mod | Efeito |
|---|---|---|---|
| `GameSession.MaxPlayers` | 3 (hardcoded) | **6** | Força o engine a aceitar 6 conexões no lobby Steam |
| `p.NetEnableListenServerSmoothing` | 0 | **1** | Habilita smoothing no listen server |
| `p.NetClientSmoothingMode` | 1 | **2** | Interpolação exponencial (mais suave) |
| `p.NetCorrectionLifetime` | 0.1 | **0.5** | Correções suavizadas em 0.5s |
| `Player NetPriority` | 1.0 | **3.0** | Players recebem 3x mais bandwidth |
| `Player MinNetUpdateFrequency` | 2 Hz | **33 Hz** | Mínimo de updates para players |

## Limitações

| Limitação | Detalhe |
|-----------|---------|
| UI do lobby | A interface do jogo foi projetada para 2-3 slots. Jogadores extras podem não aparecer na lista do lobby. |
| Spawn de inimigos | Quantidade de inimigos por encounter não muda — apenas vida e dano escalam. |
| Compatibilidade | O mod é para **Remnant: From the Ashes** (UE4). Não funciona com Remnant 2 (formato PAK diferente). |
| EnemyScaling | Depende de UE4SS e dos nomes internos de classes/propriedades do jogo. Se uma atualização mudar esses nomes, o mod precisa ser ajustado. |

---

## Arquitetura técnica

### Como o mod funciona

O `.pak` contém um único arquivo — `Remnant/Config/DefaultGame.ini` — comprimido com zlib. Quando o jogo inicia, o Unreal Engine mescla os INIs de todos os PAKs carregados. A seção sobrescrita:

```ini
[/Script/Engine.GameSession]
MaxPlayers=6
```

### Estrutura do arquivo PAK (v3)

```
┌──────────────┬─────────────────┬─────────┬────────┐
│ Entry Record │ Compressed Data │  Index  │ Footer │
│   73 bytes   │   N bytes       │ M bytes │ 44 B   │
└──────────────┴─────────────────┴─────────┴────────┘
```

**Entry Record (73 bytes)** — Metadados do arquivo empacotado:

| Offset | Tamanho | Tipo     | Descrição                         |
|--------|---------|----------|-----------------------------------|
| 0      | 8       | int64 LE | Offset do registro (= 0)         |
| 8      | 8       | int64 LE | Tamanho comprimido               |
| 16     | 8       | int64 LE | Tamanho descomprimido            |
| 24     | 4       | int32 LE | Método de compressão (1 = zlib)  |
| 28     | 20      | bytes    | SHA1 dos dados descomprimidos    |
| 48     | 4       | int32 LE | Número de blocos                 |
| 52     | 8       | int64 LE | Offset início do bloco           |
| 60     | 8       | int64 LE | Offset fim do bloco              |
| 68     | 1       | uint8    | Flag de encriptação (0 = não)    |
| 69     | 4       | int32 LE | Tamanho do bloco (65536)         |

**Índice** — Catálogo com mount point (`../../../`), nome do arquivo e réplica do entry record.

**Footer (44 bytes)** — Magic (`0x5A6F12E1`), versão (3), offset/tamanho do índice e SHA1 do índice.

### Processo de rebuild

O script `build_pak.py` executa:

1. **Extrai** o INI do PAK base via zlib decompress
2. **Substitui** o valor de `MaxPlayers` usando regex
3. **Injeta** configurações de rede escaladas para o número de jogadores
4. **Recomprime** com zlib e recalcula o SHA1
5. **Remonta** o PAK: Entry Record → dados comprimidos → índice → footer
6. **Verifica** extraindo o PAK gerado e conferindo o valor

Todas as bibliotecas usadas (`zlib`, `struct`, `hashlib`) são da stdlib do Python — zero dependências externas.

### EnemyScaling (UE4SS Lua)

O mod Lua roda dentro do UE4SS e executa um loop periódico:

1. **Conta jogadores** via `GameStateBase.PlayerArray`
2. **Identifica inimigos** varrendo personagens e excluindo pawns de `PlayerController`
3. **Escala HP** multiplicando `MaxHealth` por `1 + (extras * 0.35)`
4. **Escala dano** hookando funções de `TakeDamage` e multiplicando dano recebido por jogadores por `1 + (extras * 0.15)`
5. **Re-escala** quando o número de jogadores muda (alguém entra/sai)

O mod tenta múltiplos nomes de classes e propriedades para compatibilidade com a hierarquia do GunfireRuntime.

### NetOptimize (UE4SS Lua)

Complementa o PAK mod com otimizações que só são possíveis em runtime:

1. **Lobby override** — o jogo cria o lobby Steam com `NumPublicConnections=3` hardcoded no código C++/Blueprint. O mod força `GameSession.MaxPlayers` em runtime e hookeia `RegisterPlayer` para garantir que o engine aceite conexões além de 3
2. **Smoothing** — configura `CharacterMovementComponent` de todos os personagens com interpolação exponencial e tempos otimizados para listen server
3. **CVars** — seta variáveis do engine via `ConsoleCommand`: habilita smoothing no listen server (`p.NetEnableListenServerSmoothing`), combina pacotes de movimento, e suaviza correções de posição
4. **Prioridade de rede** — jogadores recebem `NetPriority=3.0` (3x o padrão) e `MinNetUpdateFrequency=33Hz`, garantindo que bandwidth é alocada primeiro para players
5. **Always Relevant** — marca player pawns como sempre relevantes, evitando que o engine "durma" a replicação de jogadores distantes
