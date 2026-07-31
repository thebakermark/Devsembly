#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REQUIRED = [
    Path("README.md"),
    Path("SECURITY.md"),
    Path("CONTRIBUTING.md"),
    Path("docs/vision/product-vision.md"),
    Path("docs/architecture/system-architecture.md"),
    Path("docs/security/trust-model.md"),
    Path(".devsembly/manifest.json"),
    Path(".devsembly/project-state.json"),
    Path(".devsembly/product-definition.json"),
    Path("docs/genesis/schemas/product-definition.schema.json"),
    Path("docs/product/product-definition.generated.md"),
]

missing = [str(path) for path in REQUIRED if not path.is_file()]
if missing:
    print("Missing required files:", *missing, sep="\n- ")
    sys.exit(1)

subprocess.run(
    [sys.executable, "scripts/product_projection.py", "--check"],
    check=True,
)

print("Devsembly repository foundation and generated product projection are valid.")
