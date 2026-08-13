# WaterFurnace Aurora (Modbus) — Home Assistant integration

A Home Assistant custom integration for **WaterFurnace Aurora** geothermal heat pumps — modelled for the variable-speed **Series 7** — read locally over Modbus through the Aurora ABC's RS-485 AID Tool port. No cloud, no Symphony subscription.

Built on the [waterfurnace-modbus](https://github.com/balloob/waterfurnace-modbus) device library (vendored here until it is published to PyPI) and [modbus-connection](https://github.com/home-assistant-libs/modbus-connection). The register map follows the reverse-engineered Aurora point list from [ccutrer/waterfurnace_aurora](https://github.com/ccutrer/waterfurnace_aurora).

## What you get

One Home Assistant device per heat pump, with:

- **Climate** — the communicating thermostat: heat / cool / heat-cool / off, setpoints, fan mode, and an *emergency heat* preset. One extra climate entity per IntelliZone 2 zone the unit reports.
- **Water heater** — the AXB domestic-hot-water assist: enable and tank setpoint (shown only when an AXB board is installed).
- **Sensors** — entering/leaving water and air temperatures, outdoor temperature, humidity, water flow, loop pressure, compressor and blower speeds, and drive diagnostics (discharge/suction pressure, superheat, line voltage, last fault).
- **Energy sensors** — per-load power and geothermal heat of extraction/rejection, created only when the unit has the AXB energy-monitor package.
- **Binary sensors** — compressor / blower / aux heat running, dehumidifying, lockout, emergency shutdown, pressure switches, load shed.
- **Numbers** (disabled by default — installer settings) — the four ECM blower speed presets and the loop pump's minimum/maximum speed.
- **Diagnostics download** — the last poll's outcome plus the live raw register map, which replays directly into the library's mock backend for hardware-free bug reproduction.

## Connecting

The Aurora ABC speaks **Modbus RTU on RS-485 at 19200 8E1, unit address 1** on the AID Tool port. Two ways in:

- **Network** — a transparent serial (RTU-over-TCP) gateway wired to the AID Tool port. This is the usual setup; the integration defaults to RTU framing. Pick *native Modbus TCP* only if your gateway re-frames.
- **Serial** — an RS-485 adapter on the Home Assistant host.

Setup reads the heat pump once for its identity and installed hardware — which boards are fitted, how many IntelliZone 2 zones it has — and every poll after that covers only the registers that can change.

Each sub-system is read on its own, so one block the controller will not answer costs only the entities that read it: those go unavailable while the rest keep updating, and they come back on the first poll that gets through. A poll where nothing at all answered is the heat pump being unreachable, and marks everything unavailable.

The connection is managed for you: it opens on the first read and re-establishes itself after a drop. A link that is up but silent — a bridge that keeps the socket open while the device behind it stops answering — is recycled after three timed-out polls. Either way, a heat pump that goes offline comes back on its own — no reload needed.

## Installation

### HACS

1. Make sure [HACS](https://www.hacs.xyz/) is installed.
2. Add `https://github.com/balloob/home-assistant-waterfurnace-modbus` as a custom repository of type **Integration**.
3. Download **WaterFurnace Aurora (Modbus)** and restart Home Assistant.
4. `Settings → Devices & services → Add integration → WaterFurnace Aurora (Modbus)`.

### Manual

Copy `custom_components/waterfurnace_modbus` into `/config/custom_components/` and restart.

## Vendored device library

`custom_components/waterfurnace_modbus/vendor/waterfurnace_modbus/` is a verbatim copy of the [waterfurnace-modbus](https://github.com/balloob/waterfurnace-modbus) library. It is vendored **temporarily**: once the library is on PyPI it moves to a `manifest.json` requirement and the vendor package goes away. Don't patch it here — change it upstream and re-copy.

## Develop / test

```bash
uv sync
uv run pytest
```

The tests run the real Home Assistant test harness ([pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component)) against modbus-connection's in-memory mock backend — no heat pump, no sockets.
