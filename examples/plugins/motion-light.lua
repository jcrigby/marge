-- motion-light.lua — Turns on a light when motion is detected
--
-- Demonstrates: on_state_changed(), marge.call_service(), marge.log()
-- Reacts to binary_sensor.motion and controls light.hallway

local MOTION_SENSOR = "binary_sensor.motion"
local TARGET_LIGHT  = "light.hallway"

function on_state_changed(entity_id, old_state, new_state)
    if entity_id ~= MOTION_SENSOR then
        return
    end

    if new_state == "on" and old_state ~= "on" then
        marge.log("info", "motion-light.lua: motion detected, turning on hallway light")
        marge.call_service("light", "turn_on", {
            entity_id = TARGET_LIGHT,
            brightness = 255,
        })
    elseif new_state == "off" and old_state == "on" then
        marge.log("info", "motion-light.lua: motion cleared, turning off hallway light")
        marge.call_service("light", "turn_off", {
            entity_id = TARGET_LIGHT,
        })
    end
end
