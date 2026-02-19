--[[
    EnemyScaling — Remnant: From the Ashes
    Escala vida e dano dos inimigos proporcionalmente ao numero de jogadores.

    O jogo escala nativamente ate 3 jogadores. Este mod adiciona scaling
    extra para 4+ jogadores via UE4SS.

    Requer: UE4SS v2.5.2+ (https://github.com/UE4SS-RE/RE-UE4SS)
]]

------------------------------------------------------------
-- CONFIGURACAO (edite aqui)
------------------------------------------------------------

-- Bonus POR JOGADOR acima de 3. Com 6 players:
--   HP:   1 + 3*0.35 = 2.05x
--   Dano: 1 + 3*0.15 = 1.45x
local HEALTH_PER_EXTRA = 0.35
local DAMAGE_PER_EXTRA = 0.15

-- Numero de jogadores que o jogo ja escala nativamente
local BASE_PLAYERS = 3

-- Intervalo de scan em milissegundos
local SCAN_INTERVAL_MS = 3000

-- Logs no console do UE4SS (desative para menos spam)
local LOG_ENABLED = true

------------------------------------------------------------
-- ESTADO INTERNO
------------------------------------------------------------

local currentPlayers = 0

-- Enderecos de inimigos ja escalados (weak values para GC)
local scaledActors = {}

-- Classe de inimigos descoberta (cache)
local enemyClassName = nil

-- Nomes de classes para tentar (GunfireRuntime / Remnant / generico)
local CHARACTER_CLASSES = {
    "CharacterGunfire",
    "RemnantCharacter",
    "AICharacterGunfire",
    "Character",
}

-- Nomes de propriedades de vida para tentar
local HEALTH_PROPS = {
    -- { property_de_max, property_de_current }
    { "MaxHealth",    "Health" },
    { "MaxHitPoints", "HitPoints" },
    { "HealthMax",    "HealthCurrent" },
}

-- Propriedade de vida descoberta (cache)
local healthPropIdx = nil

------------------------------------------------------------
-- UTILIDADES
------------------------------------------------------------

local function Log(msg)
    if LOG_ENABLED then
        print("[EnemyScaling] " .. msg .. "\n")
    end
end

local function ExtraPlayers()
    return math.max(currentPlayers - BASE_PLAYERS, 0)
end

local function HealthMultiplier()
    return 1.0 + ExtraPlayers() * HEALTH_PER_EXTRA
end

local function DamageMultiplier()
    return 1.0 + ExtraPlayers() * DAMAGE_PER_EXTRA
end

------------------------------------------------------------
-- PLAYER COUNT
------------------------------------------------------------

local function UpdatePlayerCount()
    local state = FindFirstOf("GameStateBase")
    if not state:IsValid() then return end

    local count = state.PlayerArray:GetArrayNum()
    if count ~= currentPlayers then
        local old = currentPlayers
        currentPlayers = count
        Log(string.format(
            "Jogadores: %d -> %d | HP x%.2f | Dano x%.2f",
            old, count, HealthMultiplier(), DamageMultiplier()
        ))

        -- Reset scaling quando player count muda,
        -- para re-escalar inimigos existentes no proximo scan
        scaledActors = {}
    end
end

------------------------------------------------------------
-- IDENTIFICACAO DE INIMIGOS
------------------------------------------------------------

-- Retorna uma tabela com os enderecos dos pawns de jogadores
local function GetPlayerPawns()
    local pawns = {}
    local controllers = FindAllOf("PlayerController")
    if not controllers then return pawns end

    for _, pc in ipairs(controllers) do
        if pc:IsValid() then
            local ok, pawn = pcall(function() return pc.Pawn end)
            if ok and pawn:IsValid() then
                pawns[pawn:GetAddress()] = true
            end
        end
    end
    return pawns
end

-- Descobre qual classe de personagem existe no jogo
local function DiscoverEnemyClass()
    if enemyClassName then return enemyClassName end

    for _, name in ipairs(CHARACTER_CLASSES) do
        local actors = FindAllOf(name)
        if actors and #actors > 0 then
            enemyClassName = name
            Log("Classe de personagens encontrada: " .. name)
            return name
        end
    end
    return nil
end

------------------------------------------------------------
-- HEALTH SCALING
------------------------------------------------------------

-- Tenta acessar HP de um ator diretamente
local function TryDirectHealth(actor, propMax, propCur)
    local ok, maxHp = pcall(function() return actor[propMax] end)
    if not ok or type(maxHp) ~= "number" or maxHp <= 0 then
        return false
    end

    local mult = HealthMultiplier()
    local newMax = maxHp * mult

    pcall(function() actor[propMax] = newMax end)
    pcall(function() actor[propCur] = newMax end)

    Log(string.format("  HP direto: %.0f -> %.0f (x%.2f)", maxHp, newMax, mult))
    return true
end

-- Tenta acessar HP via um componente (DamageableComponent, StatsComponent, etc.)
local function TryComponentHealth(actor)
    local componentNames = {
        "DamageableComponent",
        "StatsComponent",
        "HealthComponent",
    }

    for _, compName in ipairs(componentNames) do
        local ok, comp = pcall(function() return actor[compName] end)
        if ok and comp and comp:IsValid() then
            for _, props in ipairs(HEALTH_PROPS) do
                local ok2, maxHp = pcall(function() return comp[props[1]] end)
                if ok2 and type(maxHp) == "number" and maxHp > 0 then
                    local mult = HealthMultiplier()
                    local newMax = maxHp * mult

                    pcall(function() comp[props[1]] = newMax end)
                    pcall(function() comp[props[2]] = newMax end)

                    Log(string.format(
                        "  HP via %s: %.0f -> %.0f (x%.2f)",
                        compName, maxHp, newMax, mult
                    ))
                    return true
                end
            end
        end
    end
    return false
end

-- Escala a vida de um inimigo
local function ScaleEnemyHealth(actor)
    local addr = actor:GetAddress()
    if scaledActors[addr] then return end

    -- Tenta propriedades diretas
    if not healthPropIdx then
        for i, props in ipairs(HEALTH_PROPS) do
            if TryDirectHealth(actor, props[1], props[2]) then
                healthPropIdx = i
                scaledActors[addr] = true
                return
            end
        end
    else
        local props = HEALTH_PROPS[healthPropIdx]
        if TryDirectHealth(actor, props[1], props[2]) then
            scaledActors[addr] = true
            return
        end
    end

    -- Tenta via componentes
    if TryComponentHealth(actor) then
        scaledActors[addr] = true
        return
    end
end

------------------------------------------------------------
-- DAMAGE SCALING
------------------------------------------------------------

-- Caminhos de funcoes de dano para tentar hookar
local DAMAGE_HOOKS = {
    "/Script/GunfireRuntime.DamageableComponent:TakeDamage",
    "/Script/GunfireRuntime.CharacterGunfire:TakeDamage",
    "/Script/Engine.Actor:ReceiveAnyDamage",
}

local damageHooked = false

local function TryHookDamage()
    if damageHooked then return end

    for _, path in ipairs(DAMAGE_HOOKS) do
        local ok, hookId = pcall(function()
            return RegisterHook(path, function(Context, Damage, ...)
                if not Context:IsValid() then return end
                if DAMAGE_PER_EXTRA <= 0 then return end

                local mult = DamageMultiplier()
                if mult <= 1.0 then return end

                -- So escala se o alvo eh um jogador
                local playerPawns = GetPlayerPawns()
                local targetAddr = Context:get():GetAddress()

                -- Se Context eh o componente, pega o owner
                local ok2, owner = pcall(function() return Context:get():GetOwner() end)
                if ok2 and owner:IsValid() then
                    targetAddr = owner:GetAddress()
                end

                if playerPawns[targetAddr] then
                    -- Multiplica o dano recebido pelo jogador
                    if Damage and Damage.get then
                        local currentDmg = Damage:get()
                        if type(currentDmg) == "number" and currentDmg > 0 then
                            Damage:set(currentDmg * mult)
                        end
                    end
                end
            end)
        end)

        if ok and hookId then
            damageHooked = true
            Log("Hook de dano registrado: " .. path)
            return
        end
    end

    Log("Nenhum hook de dano encontrado (apenas HP sera escalado)")
end

------------------------------------------------------------
-- LOOP PRINCIPAL
------------------------------------------------------------

Log("=== EnemyScaling carregado ===")
Log(string.format(
    "Config: +%.0f%% HP / +%.0f%% Dano por jogador acima de %d",
    HEALTH_PER_EXTRA * 100, DAMAGE_PER_EXTRA * 100, BASE_PLAYERS
))

-- Tenta hookar funcoes de dano uma vez na inicializacao
TryHookDamage()

-- Scan periodico
LoopAsync(SCAN_INTERVAL_MS, function()
    UpdatePlayerCount()

    -- Nada a fazer se nao tem jogadores extras
    if ExtraPlayers() <= 0 then
        return false -- continua o loop
    end

    -- Tenta hook de dano (caso nao tenha funcionado na init)
    TryHookDamage()

    -- Descobre classe de personagem
    local className = DiscoverEnemyClass()
    if not className then
        return false -- continua o loop
    end

    -- Scan de inimigos
    local playerPawns = GetPlayerPawns()
    local actors = FindAllOf(className)
    if not actors then
        return false
    end

    for _, actor in ipairs(actors) do
        if actor:IsValid() then
            local addr = actor:GetAddress()
            -- Pula se ja escalado ou se eh um jogador
            if not scaledActors[addr] and not playerPawns[addr] then
                pcall(ScaleEnemyHealth, actor)
            end
        end
    end

    return false -- continua o loop
end)
