# Remnant: From the Ashes — 6 Player Co-op Mod

Mod que aumenta o limite de jogadores em sessões co-op do **Remnant: From the Ashes** de 3 para **6 jogadores**.

Funciona sobrescrevendo a configuração `MaxPlayers` do Unreal Engine via um arquivo `.pak` que substitui o `DefaultGame.ini` do jogo em tempo de execução.

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

### Desinstalação

Remova o arquivo `6player.pak` da pasta `~mods` (ou delete a pasta inteira).

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

## Limitações

| Limitação | Detalhe |
|-----------|---------|
| UI do lobby | A interface do jogo foi projetada para 2-3 slots. Jogadores extras podem não aparecer na lista do lobby. |
| Balanceamento | Spawn de inimigos e dificuldade escalam para até 3 jogadores no código original. |
| Rede | O netcode pode apresentar instabilidade com muitas conexões simultâneas. |
| Compatibilidade | O mod é para **Remnant: From the Ashes** (UE4). Não funciona com Remnant 2 (formato PAK diferente). |

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
3. **Recomprime** com zlib e recalcula o SHA1
4. **Remonta** o PAK: Entry Record → dados comprimidos → índice → footer
5. **Verifica** extraindo o PAK gerado e conferindo o valor

Todas as bibliotecas usadas (`zlib`, `struct`, `hashlib`) são da stdlib do Python — zero dependências externas.
