"""
Widescreen Fog Fix - keeps Borderlands 2's fog at any field of view on wide screens.

On a screen wider than 16:9, a map's height fog disappears from the ground once the field of view
passes a point: slider 107.4 on 32:9, about 125.5 on 21:9. The sprint zoom crosses it too, so the
fog pops in and out while running.

Why: the engine draws the fog as one full-screen quad at the view depth
max(30, FogMinStartDistance) * Ratio, where Ratio = 1 / sqrt(1 + tanH^2 + tanV^2), the inverse of
the frustum corner's length. Once that depth falls below the near clip plane (10 units) the whole
quad is clipped, and no geometry gets fog. That happens as soon as the corner length passes 3.

The fix points the one instruction that loads the 30.0 at the game's own shared 100.0 constant:

    RVA 0x790665   F3 0F 10 8F FC 18 00 00   movss xmm1, [edi+18FCh]
    RVA 0x79066D   F3 0F 10 25 <addr>        movss xmm4, [30.0]   <- <addr> now points at 100.0

That moves the cut-off to a corner length of 10, which is more than any usable FOV reaches. Only
memory is changed, never the exe on disk. The bytes are checked first, and on any other build of
the game nothing is written.
"""

import ctypes
import struct

from mods_base import build_mod
from unrealsdk import logging

# Borderlands2.exe, current Steam build (md5 5912a13c2fc53ad8ab2e4a4f4635dab8).
CHECK_RVA = 0x790665
CHECK = bytes.fromhex("F30F108FFC180000F30F1025")
OPERAND_RVA = 0x790671
LITERAL_30_RVA = 0x1256CB8  # the game's own value
LITERAL_100_RVA = 0x1257DA4  # the fix

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.GetModuleHandleW.restype = ctypes.c_void_p
_kernel32.GetCurrentProcess.restype = ctypes.c_void_p
_kernel32.VirtualProtect.argtypes = [
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_uint32),
]
_kernel32.FlushInstructionCache.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
PAGE_EXECUTE_READWRITE = 0x40


def _write(address: int, data: bytes) -> None:
    old = ctypes.c_uint32()
    if not _kernel32.VirtualProtect(address, len(data), PAGE_EXECUTE_READWRITE, ctypes.byref(old)):
        msg = f"VirtualProtect refused, error {ctypes.get_last_error()}"
        raise OSError(msg)
    try:
        ctypes.memmove(address, data, len(data))
    finally:
        _kernel32.VirtualProtect(address, len(data), old.value, ctypes.byref(ctypes.c_uint32()))
    _kernel32.FlushInstructionCache(_kernel32.GetCurrentProcess(), address, len(data))


def _set(fixed: bool) -> None:
    # The exe is relocated every launch, and the operand is an absolute address, so it is built
    # from the module base.
    base = _kernel32.GetModuleHandleW(None)
    found = ctypes.string_at(base + CHECK_RVA, len(CHECK))
    operand = struct.unpack("<I", ctypes.string_at(base + OPERAND_RVA, 4))[0]
    game, ours = base + LITERAL_30_RVA, base + LITERAL_100_RVA

    if found != CHECK or operand not in (game, ours):
        logging.error(
            "Widescreen Fog Fix: this isn't the game build the fix was made for, so nothing was "
            f"changed (found {found.hex(' ')} -> {operand:#x}).",
        )
        return

    wanted = ours if fixed else game
    if operand != wanted:
        _write(base + OPERAND_RVA, struct.pack("<I", wanted))
    logging.info(f"Widescreen Fog Fix: {'on' if fixed else 'off'}")


def on_enable() -> None:
    _set(True)


def on_disable() -> None:
    _set(False)


build_mod(on_enable=on_enable, on_disable=on_disable)
