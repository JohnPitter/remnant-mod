# Napkin

## Corrections
| Date | Source | What Went Wrong | What To Do Instead |
|------|--------|----------------|-------------------|
| 2026-02-19 | user/self | Escalei configs de rede proporcionalmente aos defaults UE4 (ex: 15000*2=30000). Ainda dava teleporte e lag com 6 players. | Defaults UE4 sao insuficientes como base. Usar valores altos fixos (100000 per-client) e so escalar banda total. Tick rate (NetServerMaxTickRate=60) e MAXPOSITIONERRORSQUARED alto (25.0) sao criticos. |
| 2026-02-19 | self | Coloquei settings de IpNetDriver no DefaultGame.ini. Remnant usa Steam P2P = SteamNetDriver, nao IpNetDriver. Settings provavelmente foram ignoradas. | Setar AMBOS SteamNetDriver e IpNetDriver no DefaultGame.ini. |
| 2026-02-19 | user | Criei PAK separado com DefaultEngine.ini. Crash: "Failed to find shader map for WorldGridMaterial". | NUNCA sobrescrever DefaultEngine.ini via PAK! O engine carrega ele muito cedo no boot e nosso override destroi configs criticas de shader/rendering. Tudo deve ir no DefaultGame.ini. CVars do engine devem ser setadas em runtime via UE4SS. |
| 2026-02-19 | self | Achei que SteamNetDriver no INI limitava conexoes a 3. Na verdade era problema do PC de um jogador. | Nao tirar conclusoes sem confirmar causa raiz. SteamNetDriver no DefaultGame.ini funciona ok. |
| 2026-02-20 | research | MaxPlayers no INI so configura AGameSession no engine. O lobby Steam usa NumPublicConnections que eh setado no CODIGO (C++/Blueprint) do jogo via CreateSession(). Remnant hardcoda 3. So mudar INI nao abre mais vagas no lobby. | Forcar MaxPlayers no GameSession em runtime via UE4SS + hookar RegisterPlayer para garantir que engine aceita conexoes extras. |
| 2026-02-20 | self | Usei StaticFindObject() no UE4SS Lua para ler CDO do GameSession. Crash: Unhandled exception no UE4SS. StaticFindObject pode nao existir ou crashar na API Lua do UE4SS. | NUNCA usar StaticFindObject no UE4SS Lua. Usar apenas FindAllOf/FindFirstOf com pcall para robustez. |

## User Preferences
- Linguagem: portugues brasileiro
- Projeto: mod UE4 para Remnant: From the Ashes (co-op 6 jogadores)

## Patterns That Work
- Extrair INI do PAK via `read_pak()` do build_pak.py para inspecionar conteudo
- Injetar secoes de rede no INI antes de rebuild para fix de conexao
- Configs de rede: valores per-client devem ser altos e fixos (100K), nao escalados dos defaults miseraveis do UE4
- NetServerMaxTickRate=60 eh CRITICO contra teleporte. Default 30 causa stutter visivel
- MAXPOSITIONERRORSQUARED=25.0 evita corrections constantes que causam teleporte
- Remnant usa Steam P2P: settings devem ir em SteamNetDriver (DefaultEngine.ini), nao so IpNetDriver
- NUNCA criar PAK com DefaultEngine.ini — causa crash de shader. Tudo vai no DefaultGame.ini.
- CVars do engine (p.Net*, net.*) devem ser setadas em runtime via UE4SS ConsoleCommand, nao via INI
- UE4SS Lua: usar pcall + multiplos nomes de classes/props para robustez
- Lobby override: forcar GameSession.MaxPlayers em runtime via UE4SS + hookar RegisterPlayer

## Patterns That Don't Work
- INI nao controla balanceamento de inimigos (HP, dano, spawn) — isso esta em DataTables/Blueprints
- MaxPlayers no INI (DefaultGame.ini) NAO controla tamanho do lobby Steam. O lobby eh criado com NumPublicConnections hardcoded no codigo C++/Blueprint do jogo. Precisa forcar em runtime via UE4SS.

## Domain Notes
- PAK v3 do UE4: Entry Record (73 bytes) + dados zlib + indice + footer (44 bytes)
- O jogo original suporta max 3 jogadores no co-op; mod muda DefaultGame.ini dentro do PAK
- Configuracoes de rede do UE4 estao em secoes como IpNetDriver, GameNetworkManager, Player
- DefaultGame.ini sobrescreve configs quando carregado via PAK na pasta ~mods
- GunfireRuntime: framework custom do jogo; classes como CharacterGunfire, DamageableComponent, StatsComponent
- UE4SS mods vao em `<game>/Binaries/Win64/Mods/<NomeMod>/Scripts/main.lua`
- Enemy scaling: vida e dano precisam de UE4SS (Lua runtime), nao da pra fazer via INI
- Nomes exatos de classes/props no GunfireRuntime nao confirmados sem dump — mod tenta multiplos
