--[[
    NetOptimize — Remnant: From the Ashes
    Otimiza smoothing, interpolacao e prioridade de rede para listen servers.

    O PAK mod ajusta configs no nivel do INI (bandwidth, tick rate, timeouts).
    Este mod complementa setando propriedades em runtime que nao sao
    acessiveis via INI: smoothing de movimento, interpolacao, prioridades
    de replicacao e CVars do engine.

    Requer: UE4SS v2.5.2+ (https://github.com/UE4SS-RE/RE-UE4SS)
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
local MIN_NET_UPDATE_FREQ = 33.0             -- default UE4: 2.0

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
-- LOOP PRINCIPAL
------------------------------------------------------------

Log("=== NetOptimize carregado ===")
Log(string.format(
    "Config: smooth=%.3fs, listenSmooth=%.3fs, maxDist=%.0f, playerPriority=%.1f",
    SMOOTH_LOCATION_TIME, LISTEN_SMOOTH_LOCATION_TIME,
    MAX_SMOOTH_DISTANCE, PLAYER_NET_PRIORITY
))

LoopAsync(SCAN_INTERVAL_MS, function()
    -- Tenta aplicar CVars (uma vez)
    TryApplyCVars()

    -- Scan de CharacterMovementComponents para smoothing
    ScanMovementComponents()

    -- Scan de player pawns para prioridade de rede
    ScanPlayerPawns()

    return false -- continua o loop
end)
