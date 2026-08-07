"""The controller's readable Modbus register ranges.

The Aurora ABC only answers reads that fall inside specific contiguous ranges;
a read that crosses a gap is rejected, and the board also caps a single read at
100 registers. These are the ``REGISTER_RANGES`` from the upstream
reverse-engineered map (the `ccutrer/waterfurnace_aurora
<https://github.com/ccutrer/waterfurnace_aurora>`_ project's ``registers.rb``).

The block planner uses these to merge reads only *within* a range and never
across a gap, while still clipping each read to the addresses actually used.
Everything on this device lives in the holding-register space (FC03); there are
no coils or discrete inputs — booleans are packed as bits inside holding
registers (e.g. register 30 outputs, register 31 status).
"""

from __future__ import annotations

# (low, high) inclusive — sorted, non-overlapping.
REGISTER_RANGES: tuple[tuple[int, int], ...] = (
    (0, 155),
    (170, 253),
    (260, 260),
    (280, 288),
    (300, 301),
    (320, 326),
    (340, 348),
    (360, 368),
    (400, 419),
    (440, 516),
    (550, 573),
    (600, 749),
    (800, 913),
    (1090, 1165),
    (1200, 1263),
    (2000, 2026),
    (2100, 2129),
    (2800, 2849),
    (2900, 2915),
    (2950, 2959),
    (3000, 3003),
    (3020, 3030),
    (3040, 3049),
    (3060, 3063),
    (3100, 3105),
    (3108, 3115),
    (3118, 3119),
    (3200, 3253),
    (3300, 3332),
    (3400, 3431),
    (3500, 3524),
    (3600, 3609),
    (3618, 3634),
    (3700, 3714),
    (3800, 3809),
    (3818, 3834),
    (3900, 3914),
    (12000, 12019),
    (12098, 12099),
    (12100, 12119),
    (12200, 12239),
    (12300, 12319),
    (12400, 12569),
    (12600, 12639),
    (12700, 12799),
    (20000, 20099),
    (21100, 21136),
    (21200, 21265),
    (21400, 21472),
    (21500, 21589),
    (22100, 22162),
    (22200, 22262),
    (22300, 22362),
    (22400, 22462),
    (22500, 22562),
    (22600, 22662),
    (30000, 30099),
    (31000, 31034),
    (31100, 31129),
    (31200, 31229),
    (31300, 31329),
    (31400, 31472),
    (32100, 32162),
    (32200, 32262),
    (32300, 32362),
    (32400, 32462),
    (32500, 32562),
    (32600, 32662),
    (60050, 60053),
    (60100, 60109),
    (60200, 60200),
    (61000, 61009),
)

# The ABC rejects a single Modbus read longer than 100 registers.
MAX_READ_SPAN = 100
