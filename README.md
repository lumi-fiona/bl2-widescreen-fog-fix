# Widescreen Fog Fix (Borderlands 2)

On screens wider than 16:9, Borderlands 2 stops drawing a map's fog and haze on the ground once the
field of view gets high enough. The game suddenly looks crisp and flat, and because the sprint zoom
widens the view, the fog pops in and out while you run. This mod keeps the fog at any field of view.

| Screen | Fog disappears above (FOV slider) |
|---|---|
| 32:9 (e.g. 3840×1080, 5120×1440) | 107.4 |
| 21:9 (e.g. 2560×1080, 3440×1440) | about 125.5 |
| 16:9 | about 136, which the menu doesn't reach |

The old forum advice was "go down to 108". With this mod you don't have to.

## Install

1. You need the [Borderlands 2 Python SDK / mod manager](https://bl-sdk.github.io/willow2-mod-db/).
2. Download `widescreen_fog_fix.sdkmod` from the
   [latest release](https://github.com/lumi-fiona/bl2-widescreen-fog-fix/releases/latest) and put
   it in `Borderlands 2/sdk_mods/`.
3. Start the game, open **Mods**, and enable **Widescreen Fog Fix**. It stays on between launches.

It only changes the game's memory while it runs. The exe on disk is never touched, and disabling the
mod puts the game's own value back straight away. It only affects rendering, so it's fine in co-op.
It only works on the current Steam build of the game. On any other build it detects the mismatch,
writes nothing, and says so in the log.

## What's going on

The engine draws height fog as one full-screen quad placed at the view depth

    max(30, FogMinStartDistance) × Ratio,   Ratio = 1 / sqrt(1 + tanH² + tanV²)

`tanH` and `tanV` are the tangents of half the horizontal and vertical field of view, so
`sqrt(1 + tanH² + tanV²)` is how much farther the corner of the view is than its centre. The near
clip plane sits at 10 units. Once 30 × Ratio drops below 10, which happens when the corner is more
than 3 times farther than the centre, the whole fog quad is clipped and no geometry gets fog. The
sky and translucent things still apply fog in their own shaders, which is why the sky still changes
a little.

This matches the measurements: on 32:9 the corner ratio is 2.9999 at slider 107.40 and 3.0023 at
107.45, and fog was present at the first and gone at the second. The same rule predicts the 21:9
cut-off people reported.

The fix changes which constant one instruction reads (Borderlands2.exe, RVA `0x79066D`):

    F3 0F 10 25 <addr>   movss xmm4, [30.0]   →   movss xmm4, [100.0]

It points at the game's own shared `100.0` constant instead of `30.0`. Nothing else uses this
instruction, and the constants themselves aren't edited. That moves the cut-off to a corner ratio of
10, which is more than any usable FOV reaches. The only side effect is that fog now starts from 100
units of view depth instead of 30. That's about a metre or two in front of the camera, where the fog is
effectively zero anyway.

## Hex edit without the SDK (untested)

This makes the same change permanently in the exe on disk. It has **not been tried**; the in-memory change the mod makes is
the tested one. Back up `Binaries/Win32/Borderlands2.exe` first (md5
`5912a13c2fc53ad8ab2e4a4f4635dab8`). At file offset `0x78FA71`, change `B8 6C 65 01` to
`A4 7D 65 01`. The 12 bytes before that offset must read `F3 0F 10 8F FC 18 00 00 F3 0F 10 25`. If
they don't, it's a different build, so don't edit it. Steam's "verify files" puts the original back.

## License

MIT
