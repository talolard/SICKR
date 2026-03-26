from __future__ import annotations

from pathlib import Path


def test_runtime_module_pins_nullpool_for_the_deployed_backend() -> None:
    module_path = Path(__file__).resolve().parents[2] / "infra/terraform/modules/runtime/main.tf"
    module_text = module_path.read_text(encoding="utf-8")

    assert '{ name = "DATABASE_POOL_MODE", value = "nullpool" },' in module_text
