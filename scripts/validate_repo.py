#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

REQUIRED = [
    Path("README.md"),
    Path("SECURITY.md"),
    Path("CONTRIBUTING.md"),
    Path("docs/vision/product-vision.md"),
    Path("docs/architecture/system-architecture.md"),
    Path("docs/security/trust-model.md"),
]

missing = [str(path) for path in REQUIRED if not path.is_file()]
if missing:
    print("Missing required files:", *missing, sep="\n- ")
    sys.exit(1)

print("Devsembly repository foundation is valid.")
