"""Vendored libraries for the WaterFurnace Aurora Modbus integration.

``waterfurnace_modbus`` (the device library) is copied here verbatim from
https://github.com/balloob/waterfurnace-modbus until it is published to PyPI,
at which point this package goes away in favor of a ``manifest.json``
requirement. Its only dependency, ``modbus-connection``, *is* on PyPI and is
installed through the manifest. All of the library's internal imports are
relative, so it works unchanged as a sub-package.
"""
