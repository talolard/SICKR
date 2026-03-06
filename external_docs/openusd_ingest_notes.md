# OpenUSD Ingest Notes

Sources reviewed:
- Context7 `/pixaranimationstudios/openusd` examples for `Usd.Stage.Open(...)` and basic stage inspection.

Key points used:
- Stage-level validation in Python can use `from pxr import Usd` and `Usd.Stage.Open(path)`.
- Basic inspection metadata can include:
  - default prim path (`stage.GetDefaultPrim()`)
  - traversed prim count (`sum(1 for _ in stage.Traverse())`)
  - root layer identifier (`stage.GetRootLayer().identifier`)
- We still keep a fallback validator when `pxr` is unavailable in local dev/runtime so supported extensions are accepted with minimal structural checks.

Supported formats in this repo:
- `.usda`
- `.usd`
- `.usdc`
- `.usdz`
