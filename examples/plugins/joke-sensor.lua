-- joke-sensor.lua — Fetches random jokes and publishes as sensor.joke
--
-- Demonstrates: init(), poll(), marge.set_state(), marge.http_get(), marge.log()
-- Lua equivalent of the 353-line Rust WASM plugin (examples/plugins/joke-sensor/)

local ENTITY_ID = "sensor.joke"
local JOKE_URL  = "https://official-joke-api.appspot.com/random_joke"

function init()
    marge.log("info", "joke-sensor.lua: initializing")
    marge.set_state(ENTITY_ID, "Loading...")
end

function poll()
    marge.log("debug", "joke-sensor.lua: fetching joke...")
    local resp = marge.http_get(JOKE_URL)

    if not resp or resp.status ~= 200 then
        marge.log("warn", "joke-sensor.lua: HTTP request failed")
        marge.set_state(ENTITY_ID, "Error fetching joke")
        return
    end

    -- Simple pattern-match JSON parsing (no require needed)
    local setup = resp.body:match('"setup"%s*:%s*"(.-)"')
    local punchline = resp.body:match('"punchline"%s*:%s*"(.-)"')

    if setup and punchline then
        marge.set_state(ENTITY_ID, setup .. " -- " .. punchline)
        marge.log("info", "joke-sensor.lua: updated sensor.joke")
    else
        marge.set_state(ENTITY_ID, "Failed to parse joke")
        marge.log("warn", "joke-sensor.lua: JSON parse failed")
    end
end
