# Remnant: From the Ashes — 6 Player Co-op Mod

Mod que aumenta o limite de jogadores em sessões co-op do **Remnant: From the Ashes** de 3 para **6 jogadores**, com otimizações de rede e balanceamento de inimigos.

Composto por dois módulos:
- **PAK mod** — aumenta `MaxPlayers` e ajusta configs de rede via `DefaultGame.ini`
- **EnemyScaling (UE4SS)** — escala vida e dano dos inimigos com base no número de jogadores

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
3. Copie a pasta `ue4ss/Mods/EnemyScaling/` deste repositório para dentro de `Mods/`:
   ```
   Remnant From the Ashes\
   └── Remnant\
       └── Binaries\
           └── Win64\
               ├── xinput1_3.dll         ← UE4SS
               ├── UE4SS.dll             ← UE4SS
               └── Mods\
                   └── EnemyScaling\     ← copiar aqui
                       ├── Scripts\
                       │   └── main.lua
                       └── enabled.txt
   ```
4. Inicie o jogo. O console do UE4SS mostra logs `[EnemyScaling]` confirmando que o mod está ativo.

#### Configuração do EnemyScaling

Edite os valores no topo de `main.lua`:

| Variável | Padrão | Descrição |
|---|---|---|
| `HEALTH_PER_EXTRA` | `0.35` | +35% HP por jogador acima de 3 |
| `DAMAGE_PER_EXTRA` | `0.15` | +15% dano por jogador acima de 3 |
| `BASE_PLAYERS` | `3` | Jogadores que o jogo já escala nativamente |
| `SCAN_INTERVAL_MS` | `3000` | Intervalo de scan de inimigos (ms) |

Exemplo com 6 jogadores (3 extras): HP = 2.05x, Dano = 1.45x.

### Desinstalação

- **PAK mod:** remova `6player.pak` da pasta `~mods`
- **EnemyScaling:** delete a pasta `EnemyScaling` de dentro de `Mods/`, ou remova o `enabled.txt`

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

O `build_pak.py` injeta configurações de rede **escaladas automaticamente** com base no `--players`. O fator de escala é `players / 3` (baseline do jogo). Exemplo com 6 jogadores (2.0x):

| Configuração | Padrão UE4 | 4 players | 6 players | 8 players | Efeito |
|---|---|---|---|---|---|
| `MaxClientRate` | 15,000 | 20,000 | 30,000 | 40,000 | Banda máxima por cliente (bytes/s) |
| `TotalNetBandwidth` | 32,000 | 400,000 | 600,000 | 800,000 | Banda total do servidor |
| `InitialConnectTimeout` | 30s | 45s | 75s | 105s | Tempo para handshake inicial |
| `ConnectionTimeout` | 30s | 40s | 60s | 80s | Timeout de inatividade |
| `ConfiguredInternetSpeed` | 10,000 | 20,000 | 30,000 | 40,000 | Velocidade reportada pelo cliente |
| `ClientNetSendMoveDeltaTime` | 0.0555 | 0.0416 | 0.0278 | 0.0208 | Intervalo de envio de movimento |
| `bMovementTimeDiscrepancyDetection` | true | false | false | false | Desativa kick por discrepância |

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
