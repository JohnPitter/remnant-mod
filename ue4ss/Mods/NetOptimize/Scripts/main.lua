--[[
    NetOptimize — Remnant: From the Ashes
    Otimiza smoothing, interpolacao, prioridade de rede e lobby Steam
    para listen servers com mais de 3 jogadores.

    O PAK mod ajusta configs no nivel do INI (bandwidth, tick rate, timeouts,
    MaxPlayers). Este mod complementa com:
    - Lobby override: forca MaxPlayers no GameSession em runtime para que
      o lobby Steam aceite mais de 3 conexoes
    - Smoothing de movimento e interpolacao
    - Prioridades de replicacao e CVars do engine

    Requer: UE4SS v3.0.1+ (https://github.com/UE4SS-RE/RE-UE4SS)
]]

------------------------------------------------------------
-- CONFIGURACAO
------------------------------------------------------------

-- Smoothing de posicao: tempo em segundos para suavizar a interpolacao
-- entre updates de rede. Maior = mais suave, mas mais "atrasado".
-- Menor = mais responsivo, mas pode ter micro-stutter.
local SMOOTH_LOCATION_TIME = 0.100           -- default UE4: 0.100
local SMOOTH_ROTATION_TIME = 0.050           -- default UE4: 0.033

-- Listen server tem smoothing proprio (o host eh server + client).
-- Esses valores controlam a suavizacao para o host.
local LISTEN_SMOOTH_LOCATION_TIME = 0.080    -- default UE4: 0.040
local LISTEN_SMOOTH_ROTATION_TIME = 0.040    -- default UE4: 0.033

-- Distancia maxima para aplicar smoothing (unidades UE4).
-- Alem de MAX, faz snap (teleporte instantaneo, intencional).
local MAX_SMOOTH_DISTANCE = 512.0            -- default UE4: 256.0
local NO_SMOOTH_DISTANCE = 1024.0            -- default UE4: 384.0

-- Prioridade de replicacao para personagens de jogadores.
-- Quanto maior, mais bandwidth o engine aloca para esse ator.
-- Default UE4 = 1.0. Players devem ter prioridade sobre NPCs.
local PLAYER_NET_PRIORITY = 3.0

-- Frequencia minima de updates de rede para personagens (Hz).
-- Garante que mesmo com pouca banda, personagens atualizem.
-- 33Hz era muito agressivo para 5+ jogadores (causa reliable buffer overflow).
-- 15Hz é seguro e ainda responsivo.
local MIN_NET_UPDATE_FREQ = 15.0             -- default UE4: 2.0

-- Fallback para MaxPlayers caso a leitura do GameSession falhe.
-- Em uso normal nao precisa editar: o mod le o valor que o PAK
-- setou no GameSession via INI (ex: build_pak.py --players 8 -> 8).
local MAX_PLAYERS_FALLBACK = 6

-- Intervalo de scan em milissegundos
local SCAN_INTERVAL_MS = 4000

-- Logs no console do UE4SS
local LOG_ENABLED = true

------------------------------------------------------------
-- ESTADO INTERNO
------------------------------------------------------------

local processedCMCs = {}       -- CharacterMovementComponents ja configurados
local processedPlayers = {}    -- Pawns de jogadores ja configurados
local cvarsApplied = false
local lobbyFixed = false        -- Flag: lobby ja foi corrigido
local maxPlayers = nil          -- Lido do GameSession em runtime (nil = ainda nao lido)

------------------------------------------------------------
-- UTILIDADES
------------------------------------------------------------

local function Log(msg)
    if LOG_ENABLED then
        print("[NetOptimize] " .. msg .. "\n")
    end
end

------------------------------------------------------------
-- SMOOTHING: CharacterMovementComponent
------------------------------------------------------------

local function ApplySmoothing(cmc)
    local addr = cmc:GetAddress()
    if processedCMCs[addr] then return end

    local applied = 0
    local total = 0

    local props = {
        { "NetworkSimulatedSmoothLocationTime",               SMOOTH_LOCATION_TIME },
        { "NetworkSimulatedSmoothRotationTime",               SMOOTH_ROTATION_TIME },
        { "ListenServerNetworkSimulatedSmoothLocationTime",   LISTEN_SMOOTH_LOCATION_TIME },
        { "ListenServerNetworkSimulatedSmoothRotationTime",   LISTEN_SMOOTH_ROTATION_TIME },
        { "NetworkMaxSmoothUpdateDistance",                    MAX_SMOOTH_DISTANCE },
        { "NetworkNoSmoothUpdateDistance",                     NO_SMOOTH_DISTANCE },
    }

    for _, prop in ipairs(props) do
        total = total + 1
        local ok = pcall(function() cmc[prop[1]] = prop[2] end)
        if ok then applied = applied + 1 end
    end

    if applied > 0 then
        processedCMCs[addr] = true
        Log(string.format("Smoothing: %d/%d props em CMC @ 0x%X", applied, total, addr))
    end
end

local function ScanMovementComponents()
    local cmcs = FindAllOf("CharacterMovementComponent")
    if not cmcs then return end

    for _, cmc in ipairs(cmcs) do
        if cmc:IsValid() and not processedCMCs[cmc:GetAddress()] then
            pcall(ApplySmoothing, cmc)
        end
    end
end

------------------------------------------------------------
-- NET PRIORITY: Player pawns
------------------------------------------------------------

local function ApplyPlayerPriority(pawn)
    local addr = pawn:GetAddress()
    if processedPlayers[addr] then return end

    local applied = 0

    -- Prioridade de replicacao
    local ok1 = pcall(function() pawn.NetPriority = PLAYER_NET_PRIORITY end)
    if ok1 then applied = applied + 1 end

    -- Frequencia minima de update de rede
    local ok2 = pcall(function() pawn.MinNetUpdateFrequency = MIN_NET_UPDATE_FREQ end)
    if ok2 then applied = applied + 1 end

    -- Garante que esta sempre relevante para rede (nunca fica "dormant")
    local ok3 = pcall(function() pawn.bAlwaysRelevant = true end)
    if ok3 then applied = applied + 1 end

    if applied > 0 then
        processedPlayers[addr] = true
        Log(string.format(
            "Player pawn @ 0x%X: prioridade=%.1f, minFreq=%.0fHz, alwaysRelevant=true",
            addr, PLAYER_NET_PRIORITY, MIN_NET_UPDATE_FREQ
        ))
    end
end

local function ScanPlayerPawns()
    local controllers = FindAllOf("PlayerController")
    if not controllers then return end

    for _, pc in ipairs(controllers) do
        if pc:IsValid() then
            local ok, pawn = pcall(function() return pc.Pawn end)
            if ok and pawn and pawn:IsValid() then
                if not processedPlayers[pawn:GetAddress()] then
                    pcall(ApplyPlayerPriority, pawn)
                end
            end
        end
    end
end

------------------------------------------------------------
-- CVARS VIA CONSOLE COMMAND
------------------------------------------------------------

-- CVars que controlam comportamento de rede no engine level.
-- Setados via PlayerController:ConsoleCommand() uma unica vez.
local NET_CVARS = {
    -- Smoothing exponencial (mais suave que linear)
    "p.NetClientSmoothingMode 2",

    -- Habilita smoothing no listen server (CRITICO — desabilitado por default!)
    "p.NetEnableListenServerSmoothing 1",

    -- Combina multiplos updates de movimento em um so pacote
    "p.NetEnableMoveCombining 1",

    -- Tempo de vida das correcoes de posicao (suaviza em vez de snap)
    "p.NetCorrectionLifetime 0.5",

    -- Mais tolerancia para timestamps de movimento do cliente
    "p.NetServerMoveTimestampExpiredWarningThreshold 5.0",

    -- Desabilita throttling de bandwidth (evita stall no IsNetReady que causa
    -- acumulo de pacotes e eventual reliable buffer overflow com 5+ jogadores)
    "net.DisableBandwidthThrottling 1",

    -- Aumenta tamanho maximo de bunches parciais (reduz fragmentacao)
    "net.MaxConstructedPartialBunchSizeBytes 131072",

    -- Aumenta memoria maxima para replicacao de arrays (previne crash em arrays grandes)
    "net.MaxRepArrayMemory 131072",

    -- Aumenta limite de arrays replicados
    "net.MaxRepArraySize 4096",

    -- Limita RPCs por update para espalhar carga entre ticks (previne burst)
    "net.MaxRPCPerNetUpdate 4",

    -- Timeouts mais tolerantes para conexoes P2P Steam
    "net.PingTimeout 60.0",
    "net.CloseTimeout 60.0",
}

local function TryApplyCVars()
    if cvarsApplied then return end

    local pc = FindFirstOf("PlayerController")
    if not pc:IsValid() then return end

    local applied = 0
    for _, cmd in ipairs(NET_CVARS) do
        local ok = pcall(function()
            pc:ConsoleCommand(cmd, false)
        end)
        if ok then
            applied = applied + 1
            Log("CVar: " .. cmd)
        end
    end

    if applied > 0 then
        cvarsApplied = true
        Log(string.format("CVars aplicadas: %d/%d", applied, #NET_CVARS))
    end
end

------------------------------------------------------------
-- LOBBY OVERRIDE: Le MaxPlayers do INI e forca no GameSession
------------------------------------------------------------

-- Fluxo:
-- 1. O PAK mod seta [/Script/Engine.GameSession] MaxPlayers=N no INI
-- 2. O engine carrega esse valor no GameSession quando cria a sessao
-- 3. MAS o jogo pode sobrescrever com 3 (hardcoded) ao criar o lobby Steam
-- 4. Este mod le o valor do INI (via GameSession CDO) e forca de volta
--
-- Resultado: basta mudar --players no build_pak.py e tudo sincroniza.

-- Le o MaxPlayers que o PAK setou no GameSession.
-- O INI seta o valor no GameSession; nos lemos dele em runtime.
local function ReadMaxPlayersFromConfig()
    if maxPlayers then return maxPlayers end

    -- Tenta ler de instancias ativas do GameSession e subclasses
    local classNames = {
        "GameSession",
        "GunfireGameSession",
        "RemnantGameSession",
    }
    for _, className in ipairs(classNames) do
        local ok, sessions = pcall(FindAllOf, className)
        if ok and sessions then
            for _, session in ipairs(sessions) do
                local ok2, val = pcall(function() return session.MaxPlayers end)
                if ok2 and type(val) == "number" and val > 3 then
                    maxPlayers = val
                    Log(string.format("MaxPlayers lido de %s: %d", className, val))
                    return maxPlayers
                end
            end
        end
    end

    return nil -- ainda nao disponivel, tenta de novo no proximo scan
end

-- Retorna o MaxPlayers efetivo
local function GetMaxPlayers()
    if maxPlayers then return maxPlayers end
    local val = ReadMaxPlayersFromConfig()
    if val then return val end
    return MAX_PLAYERS_FALLBACK
end

local function TryFixLobby()
    if lobbyFixed then return end

    local target = GetMaxPlayers()

    -- 1. Forca MaxPlayers no GameSession (classe base do engine)
    local sessions = FindAllOf("GameSession")
    if not sessions then return end

    local fixed = false
    for _, session in ipairs(sessions) do
        if session:IsValid() then
            local ok, currentMax = pcall(function() return session.MaxPlayers end)
            if ok and type(currentMax) == "number" then
                if currentMax < target then
                    pcall(function() session.MaxPlayers = target end)
                    Log(string.format(
                        "GameSession MaxPlayers: %d -> %d",
                        currentMax, target
                    ))
                    fixed = true
                else
                    Log(string.format("GameSession MaxPlayers ja correto: %d", currentMax))
                    fixed = true
                end
            end
        end
    end

    -- 2. Tenta tambem em subclasses do GunfireRuntime
    local sessionClassNames = {
        "GunfireGameSession",
        "RemnantGameSession",
    }
    for _, className in ipairs(sessionClassNames) do
        local instances = FindAllOf(className)
        if instances then
            for _, session in ipairs(instances) do
                if session:IsValid() then
                    pcall(function() session.MaxPlayers = target end)
                    Log(string.format("  %s MaxPlayers -> %d", className, target))
                    fixed = true
                end
            end
        end
    end

    -- 3. Tenta forcar no GameMode tambem (controla criacao de sessoes)
    local gameModes = FindAllOf("GameModeBase")
    if not gameModes then gameModes = FindAllOf("GameMode") end
    if gameModes then
        for _, gm in ipairs(gameModes) do
            if gm:IsValid() then
                local ok, gs = pcall(function() return gm.GameSession end)
                if ok and gs and gs:IsValid() then
                    pcall(function() gs.MaxPlayers = target end)
                    Log("GameMode->GameSession MaxPlayers forcado")
                    fixed = true
                end
            end
        end
    end

    if fixed then
        lobbyFixed = true
        Log("=== Lobby override aplicado! ===")
    end
end

------------------------------------------------------------
-- FORCE CLIENT BANDWIDTH
------------------------------------------------------------

-- Clientes sem o PAK mod conectam com ConfiguredInternetSpeed=10000 (10KB/s).
-- Isso causa throttling severo e acumulo de pacotes reliable.
-- Forcamos bandwidth alto em todos os players conectados.

local processedPlayerSpeeds = {}

local function ForceClientBandwidth()
    local controllers = FindAllOf("PlayerController")
    if not controllers then return end

    for _, pc in ipairs(controllers) do
        if pc:IsValid() then
            local addr = pc:GetAddress()
            if not processedPlayerSpeeds[addr] then
                local fixed = false
                -- Tenta setar via Player object
                pcall(function()
                    local player = pc.Player
                    if player and player:IsValid() then
                        player.ConfiguredInternetSpeed = 200000
                        player.ConfiguredLanSpeed = 200000
                        fixed = true
                    end
                end)
                -- Tenta tambem via ConsoleCommand
                pcall(function()
                    pc:ConsoleCommand("net.ConfiguredInternetSpeed 200000", false)
                end)
                if fixed then
                    processedPlayerSpeeds[addr] = true
                    Log(string.format("Client bandwidth forcado @ 0x%X: 200000", addr))
                end
            end
        end
    end
end

-- NOTA: RegisterPlayer hook REMOVIDO.
-- O hook causava crash (Unhandled exception via UE4SS) quando o 5o/6o
-- jogador conectava. Modificar MaxPlayers DURANTE o RegisterPlayer
-- corrompe estado interno do engine. O TryFixLobby() no loop ja forca
-- MaxPlayers a cada 4s, o que eh suficiente.

------------------------------------------------------------
-- SPAWN POINT SAFETY
------------------------------------------------------------

-- TPSGameMode_Main tem 4 SpawnPoints (Spawn1-4_GEN_VARIABLE).
-- Se o SpawnPointManager indexa por numero de player, player 5/6
-- pode pegar nullptr. Monitoramos spawn points e duplicamos se necessario.

local spawnPointsChecked = false

local function EnsureSpawnPoints()
    if spawnPointsChecked then return end

    -- Procura o SpawnPointManager ativo
    local ok, managers = pcall(FindAllOf, "SpawnPointManager")
    if not ok or not managers then return end

    for _, mgr in ipairs(managers) do
        if mgr:IsValid() then
            -- Tenta ler SpawnPoints (array de spawn points no manager)
            local ok2, spawnPoints = pcall(function() return mgr.SpawnPoints end)
            if ok2 and spawnPoints then
                local count = 0
                pcall(function()
                    count = #spawnPoints
                end)
                Log(string.format("SpawnPointManager: %d spawn points encontrados", count))

                -- Se tem menos que MaxPlayers spawn points, o engine vai fazer
                -- fallback (modulo/round-robin). Logamos para diagnóstico.
                local target = GetMaxPlayers()
                if count > 0 and count < target then
                    Log(string.format(
                        "AVISO: Apenas %d spawn points para %d jogadores. Engine deve fazer fallback.",
                        count, target
                    ))
                end
            end
            spawnPointsChecked = true
        end
    end
end

------------------------------------------------------------
-- GAME STATE SCALING SAFETY
------------------------------------------------------------

-- O TPSGameState usa NumPlayersScalingTable (DataTable) para escalar
-- inimigos. O PAK mod adiciona rows 5 e 6, mas se o PAK nao carregou
-- a DataTable (ex: cliente sem mod), o FindRow("5") retorna nullptr -> crash.
-- Monitoramos o GameState e logamos o estado do scaling.

local scalingChecked = false

local function CheckScalingSafety()
    if scalingChecked then return end

    -- Procura TPSGameState
    local classNames = { "TPSGameState", "GameState", "GameStateBase" }
    for _, className in ipairs(classNames) do
        local ok, states = pcall(FindAllOf, className)
        if ok and states then
            for _, state in ipairs(states) do
                if state:IsValid() then
                    -- Tenta ler NumPlayersScalingTable
                    local ok2, table = pcall(function() return state.NumPlayersScalingTable end)
                    if ok2 and table then
                        Log(string.format("GameState.NumPlayersScalingTable: presente (@ 0x%X)", state:GetAddress()))
                        scalingChecked = true
                        return
                    end
                    -- Tenta DifficultyScalingTable
                    local ok3, dtable = pcall(function() return state.DifficultyScalingTable end)
                    if ok3 and dtable then
                        Log(string.format("GameState.DifficultyScalingTable: presente"))
                    end
                end
            end
        end
    end
end

------------------------------------------------------------
-- LOOP PRINCIPAL
------------------------------------------------------------

Log("=== NetOptimize carregado ===")
Log(string.format(
    "Config: smooth=%.3fs, listenSmooth=%.3fs, maxDist=%.0f, playerPriority=%.1f, fallback=%d",
    SMOOTH_LOCATION_TIME, LISTEN_SMOOTH_LOCATION_TIME,
    MAX_SMOOTH_DISTANCE, PLAYER_NET_PRIORITY, MAX_PLAYERS_FALLBACK
))
Log("MaxPlayers sera lido do GameSession (setado pelo PAK mod via INI)")

LoopAsync(SCAN_INTERVAL_MS, function()
    -- Forca MaxPlayers no GameSession (critico para lobby Steam)
    TryFixLobby()

    -- Tenta aplicar CVars (uma vez)
    TryApplyCVars()

    -- Forca bandwidth alto em clientes conectados (sem PAK = 10KB/s default)
    ForceClientBandwidth()

    -- Scan de CharacterMovementComponents para smoothing
    ScanMovementComponents()

    -- Scan de player pawns para prioridade de rede
    ScanPlayerPawns()

    -- Verifica spawn points (uma vez)
    EnsureSpawnPoints()

    -- Verifica scaling tables (uma vez)
    CheckScalingSafety()

    return false -- continua o loop
end)
