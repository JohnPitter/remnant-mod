# Remnant: From the Ashes — 6 Player Co-op Mod

Mod que aumenta o limite de jogadores em sessões co-op do **Remnant: From the Ashes** de 3 para **6 jogadores**, com otimizações de rede, scaling de inimigos nativo e balanceamento extra via Lua.

## Quem precisa instalar o quê

| Componente | Host (quem cria a sala) | Clientes (quem entra) |
|---|---|---|
| `6player.pak` | **Obrigatório** | **Obrigatório** |
| UE4SS | **Obrigatório** | Opcional |
| NetOptimize | **Obrigatório** (libera o lobby) | Opcional (melhora rede) |
| EnemyScaling | Opcional (balanceamento) | Não precisa |

> **Resumo:** Todos precisam do PAK. O **host** precisa do UE4SS + NetOptimize para o lobby aceitar mais de 3 pessoas. EnemyScaling é opcional.

---

## Instalação completa (passo a passo)

### Passo 1 — Localizar a pasta do jogo

1. Abra a **Steam**, clique com o botão direito em **Remnant: From the Ashes**
2. Vá em **Gerenciar** > **Ver arquivos locais**
3. A pasta que abrir é a raiz do jogo. Caminho típico:
   ```
   C:\Program Files (x86)\Steam\steamapps\common\Remnant From the Ashes\
   ```

Você vai precisar de duas pastas dentro dela:

| O quê | Caminho |
|---|---|
| PAKs do jogo | `Remnant From the Ashes\Remnant\Content\Paks\` |
| Binários (EXE) | `Remnant From the Ashes\Remnant\Binaries\Win64\` |

### Passo 2 — Instalar o PAK mod (todos os jogadores)

1. Baixe o arquivo **`6player.pak`** da página de [Releases](../../releases)
2. Dentro da pasta de PAKs, crie uma pasta chamada **`~mods`** (se não existir)
3. Copie `6player.pak` para dentro de `~mods`

Resultado:
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

> O prefixo `~` garante que o Unreal Engine carregue os mods **depois** dos arquivos originais.

### Passo 3 — Instalar o UE4SS (obrigatório para o host)

O UE4SS é o framework que permite os mods Lua (NetOptimize e EnemyScaling) rodarem.

1. Baixe o **UE4SS v3.0.1** (ou mais recente) na página de [Releases do UE4SS](https://github.com/UE4SS-RE/RE-UE4SS/releases/tag/v3.0.1)
   - Pegue o arquivo **`UE4SS_v3.0.1.zip`** (não a versão "zDEV")
2. Extraia **todo o conteúdo do zip** na pasta de binários do jogo:
   ```
   Remnant From the Ashes\Remnant\Binaries\Win64\
   ```
3. Confira que esses arquivos existem:
   ```
   Win64\
   ├── dwmapi.dll       ← DLL proxy do UE4SS
   ├── UE4SS.dll        ← Core do UE4SS
   ├── UE4SS-settings.ini
   └── Mods\            ← Pasta onde vão os mods Lua
       └── ...          ← Mods padrão do UE4SS
   ```

> **Se você tinha UE4SS v2.5.2 ou anterior:** delete o `xinput1_3.dll` antigo! O v3.0+ usa `dwmapi.dll` como proxy. Manter o `xinput1_3.dll` junto causa crash.

### Passo 4 — Instalar NetOptimize (obrigatório para o host)

**Este é o mod que libera o lobby para mais de 3 jogadores.** Sem ele, o jogo rejeita conexões extras mesmo com o PAK instalado.

1. Copie a pasta `ue4ss/Mods/NetOptimize/` deste repositório para dentro da pasta `Mods/` do UE4SS:
   ```
   Win64\
   └── Mods\
       └── NetOptimize\
           ├── Scripts\
           │   └── main.lua
           └── enabled.txt
   ```

### Passo 5 — Instalar EnemyScaling (opcional)

Escala vida e dano dos inimigos para não ficar fácil demais com 6 pessoas. Só precisa estar no host.

1. Copie a pasta `ue4ss/Mods/EnemyScaling/` para dentro da pasta `Mods/` do UE4SS:
   ```
   Win64\
   └── Mods\
       └── EnemyScaling\
           ├── Scripts\
           │   └── main.lua
           └── enabled.txt
   ```

### Resultado final

```
Remnant From the Ashes\
└── Remnant\
    ├── Content\
    │   └── Paks\
    │       └── ~mods\
    │           └── 6player.pak              ← PAK mod
    └── Binaries\
        └── Win64\
            ├── Remnant.exe
            ├── dwmapi.dll                   ← UE4SS (proxy)
            ├── UE4SS.dll                    ← UE4SS
            └── Mods\
                ├── NetOptimize\             ← lobby + rede
                │   ├── Scripts\main.lua
                │   └── enabled.txt
                └── EnemyScaling\            ← balanceamento
                    ├── Scripts\main.lua
                    └── enabled.txt
```

### Verificando que tudo funciona

1. Inicie o jogo. Se o UE4SS estiver correto, uma janela de console aparece junto com o jogo.
2. No console, procure por:
   ```
   [NetOptimize] === NetOptimize carregado ===
   [NetOptimize] GameSession MaxPlayers: 3 -> 6
   [NetOptimize] === Lobby override aplicado! ===
   ```
3. Se aparecer "Lobby override aplicado", o lobby Steam vai aceitar 6 conexões.
4. Para conectar, os amigos usam **convite Steam** ou **Entrar no Jogo** pelo perfil do host.

---

## Como conectar (multiplayer)

O Remnant usa **Steam P2P** — não precisa de servidor dedicado.

1. O **host** inicia o jogo e cria uma sessão (jogo normal)
2. Os outros jogadores conectam por:
   - **Convite Steam:** o host abre o overlay Steam (Shift+Tab) e convida os amigos
   - **Join Game:** os amigos clicam com o botão direito no perfil do host no Steam > "Entrar no Jogo"
3. A UI do lobby do jogo só mostra 2-3 slots, mas jogadores extras entram normalmente

---

## Desinstalação

| Componente | Como remover |
|---|---|
| PAK mod | Delete `6player.pak` da pasta `~mods` |
| NetOptimize | Delete a pasta `Mods/NetOptimize/` ou remova o `enabled.txt` |
| EnemyScaling | Delete a pasta `Mods/EnemyScaling/` ou remova o `enabled.txt` |
| UE4SS inteiro | Delete `dwmapi.dll`, `UE4SS.dll`, `UE4SS-settings.ini` e a pasta `Mods/` de `Win64/` |

---

## Configuração avançada

### EnemyScaling

Edite os valores no topo de `EnemyScaling/Scripts/main.lua`:

| Variável | Padrão | Descrição |
|---|---|---|
| `HEALTH_PER_EXTRA` | `0.35` | +35% HP por jogador acima de 3 |
| `DAMAGE_PER_EXTRA` | `0.15` | +15% dano por jogador acima de 3 |
| `BASE_PLAYERS` | `3` | Jogadores que o jogo já escala nativamente |
| `SCAN_INTERVAL_MS` | `3000` | Intervalo de scan de inimigos (ms) |

Exemplo com 6 jogadores (3 extras): HP = 2.05x, Dano = 1.45x.

### NetOptimize

Edite os valores no topo de `NetOptimize/Scripts/main.lua`:

| Variável | Padrão | Descrição |
|---|---|---|
| `MAX_PLAYERS_FALLBACK` | `6` | Fallback caso a leitura do GameSession falhe (normalmente lê do PAK automaticamente) |
| `SMOOTH_LOCATION_TIME` | `0.100` | Tempo de interpolação de posição (s) |
| `LISTEN_SMOOTH_LOCATION_TIME` | `0.080` | Interpolação no listen server (s) |
| `MAX_SMOOTH_DISTANCE` | `512.0` | Distância máx para suavizar (além disso, snap) |
| `PLAYER_NET_PRIORITY` | `3.0` | Prioridade de rede dos jogadores (default UE4: 1.0) |
| `MIN_NET_UPDATE_FREQ` | `33.0` | Update mínimo de rede para jogadores (Hz) |

CVars setadas automaticamente via console:

| CVar | Valor | Efeito |
|---|---|---|
| `p.NetEnableListenServerSmoothing` | `1` | Habilita smoothing no listen server (desabilitado por default!) |
| `p.NetClientSmoothingMode` | `2` | Interpolação exponencial (mais suave que linear) |
| `p.NetEnableMoveCombining` | `1` | Combina updates de movimento em pacotes maiores |
| `p.NetCorrectionLifetime` | `0.5` | Correções de posição são suavizadas em 0.5s em vez de snap |

### Gerando um PAK customizado

Se quiser um número diferente de jogadores, use os scripts Python:

```bash
# Requer Python 3 (sem dependências externas)

# 1. Gerar a DataTable com scaling para 6 players
python rebuild_scaling.py

# 2. Gerar o PAK com INI + DataTable
python build_pak.py --players 8
```

| Flag | Padrão | Descrição |
|---|---|---|
| `--players` | `6` | Número máximo de jogadores |
| `--input` | `4player.pak` | PAK base para extrair o INI |
| `--output` | `{N}player.pak` | Nome do arquivo de saída |
| `--no-scaling` | — | Não incluir DataTable de scaling (só INI) |

> O `rebuild_scaling.py` extrai a DataTable original do jogo e gera versões com 6 rows. O `build_pak.py` inclui automaticamente esses arquivos se existirem em `modified/`.
>
> O NetOptimize lê o `MaxPlayers` do PAK automaticamente — não precisa editar nada no Lua ao mudar `--players`.

---

## Limitações

| Limitação | Detalhe |
|---|---|
| UI do lobby | A interface do jogo foi projetada para 2-3 slots. Jogadores extras podem não aparecer na lista do lobby, mas entram normalmente. |
| Spawn de inimigos | O PAK escala SpawnQuantity e SpawnWeight nativamente para 5-6P. Vida e dano extras vêm do EnemyScaling (Lua). |
| Compatibilidade | O mod é para **Remnant: From the Ashes** (UE4). Não funciona com Remnant 2 (formato PAK diferente). |
| Host obrigatório | O host **precisa** ter UE4SS + NetOptimize para o lobby aceitar mais de 3 conexões. |
| EnemyScaling | Depende de UE4SS e dos nomes internos de classes/propriedades do jogo. Se uma atualização mudar esses nomes, o mod precisa ser ajustado. |

---

## Como funciona (detalhes técnicos)

### Camadas do mod

O mod opera em três camadas:

```
┌──────────────────────────────────────────────────────────┐
│  Camada 4: UE4SS Lua (runtime)                           │
│  NetOptimize: força GameSession.MaxPlayers = 6,          │
│  seta CVars, smoothing, prioridade de rede               │
│  EnemyScaling: escala HP/dano dos inimigos               │
├──────────────────────────────────────────────────────────┤
│  Camada 3: DataTable Stats_Scaling_NumPlayers (PAK mod)  │
│  Tabela de scaling nativa do jogo, reconstruída com      │
│  rows para 5P e 6P (spawn quantity/weight)               │
├──────────────────────────────────────────────────────────┤
│  Camada 2: DefaultGame.ini (PAK mod)                     │
│  MaxPlayers=6, SteamNetDriver, IpNetDriver,              │
│  GameNetworkManager (bandwidth, tick rate, timeouts)      │
├──────────────────────────────────────────────────────────┤
│  Camada 1: Jogo original                                 │
│  MaxPlayers=3, defaults de rede do UE4, DataTable 1-4P   │
└──────────────────────────────────────────────────────────┘
```

**Por que precisa de 4 camadas?**
- O PAK muda `MaxPlayers` no INI, mas o jogo cria o lobby Steam com `NumPublicConnections=3` **hardcoded no código**. Só mudar o INI não abre mais vagas no lobby.
- A DataTable original só tem scaling para 1-4 jogadores. Quando o 5º player entra, `FindRow("5")` retorna `nullptr` e o jogo **crasha**. O PAK mod inclui a tabela com 6 rows.
- O NetOptimize força `GameSession.MaxPlayers` em runtime via UE4SS, fazendo o engine aceitar conexões extras.
- CVars de smoothing/interpolação não podem ser setadas via INI — precisam de `ConsoleCommand` em runtime.

### Otimizações de rede do PAK

| Configuração | Padrão UE4 | Mod | Efeito |
|---|---|---|---|
| `SteamNetDriver.NetServerMaxTickRate` | 30 | **60** | Tick rate do servidor (Hz) |
| `SteamNetDriver.MaxClientRate` | 15,000 | **100,000** | Banda máxima por cliente (bytes/s) |
| `ConfiguredInternetSpeed` | 10,000 | **100,000** | Velocidade reportada pelo cliente |
| `TotalNetBandwidth` | 32,000 | **100K x N** | Banda total (600K para 6 players) |
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

### Stats_Scaling_NumPlayers — DataTable de scaling nativo

O jogo usa a DataTable `Stats_Scaling_NumPlayers` para escalar spawns de inimigos por número de jogadores. A tabela original tem **4 rows** (1P–4P). Quando o 5º ou 6º jogador conecta, o engine faz `FindRow("5")` → `nullptr` → **crash**.

O PAK mod inclui a DataTable **reconstruída com 6 rows**:

| Property | 1P | 2P | 3P | 4P | 5P | 6P |
|---|---|---|---|---|---|---|
| SpawnQuantityScalar | 1.00 | 1.33 | 1.66 | 2.00 | **2.33** | **2.66** |
| SpawnWeightScalar | 1.00 | 1.50 | 1.75 | 1.60 | **1.60** | **1.60** |
| Demais scalars | 1.00 | 1.00 | 1.00 | 1.00 | **1.00** | **1.00** |

Valores para 5P e 6P foram extrapolados linearmente a partir dos originais. Para regenerar com valores diferentes, edite e execute `rebuild_scaling.py`.

### Estrutura do arquivo PAK (v8)

```
┌────────────────────────────┬────────────────────────────┬───┬─────────┬────────┐
│ Entry 1: Record+Compressed │ Entry 2: Record+Compressed │...│  Index  │ Footer │
│         73+N bytes         │         73+M bytes         │   │ K bytes │ 44 B   │
└────────────────────────────┴────────────────────────────┴───┴─────────┴────────┘
```

O `.pak` contém 3 arquivos comprimidos com zlib:
- `Remnant/Config/DefaultGame.ini` — MaxPlayers + configs de rede
- `Remnant/Content/_Core/Stats/Stats_Scaling_NumPlayers.uasset` — header da DataTable (6 rows)
- `Remnant/Content/_Core/Stats/Stats_Scaling_NumPlayers.uexp` — dados da DataTable (6 rows)

Quando o jogo inicia, o Unreal Engine mescla os INIs e sobrescreve assets de todos os PAKs carregados.

### EnemyScaling (UE4SS Lua)

1. **Conta jogadores** via `GameStateBase.PlayerArray`
2. **Identifica inimigos** varrendo personagens e excluindo pawns de `PlayerController`
3. **Escala HP** multiplicando `MaxHealth` por `1 + (extras * 0.35)`
4. **Escala dano** hookando funções de `TakeDamage` e multiplicando dano recebido por jogadores por `1 + (extras * 0.15)`
5. **Re-escala** quando o número de jogadores muda (alguém entra/sai)

### NetOptimize (UE4SS Lua)

1. **Lobby override** — força `GameSession.MaxPlayers` em runtime e hookeia `RegisterPlayer` para garantir que o engine aceite conexões além de 3
2. **Smoothing** — configura `CharacterMovementComponent` com interpolação exponencial e tempos otimizados para listen server
3. **CVars** — seta variáveis do engine via `ConsoleCommand`: habilita smoothing no listen server, combina pacotes de movimento, e suaviza correções de posição
4. **Prioridade de rede** — jogadores recebem `NetPriority=3.0` (3x o padrão) e `MinNetUpdateFrequency=33Hz`
5. **Always Relevant** — marca player pawns como sempre relevantes, evitando que o engine "durma" a replicação de jogadores distantes
