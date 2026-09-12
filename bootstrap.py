from __future__ import annotations

import os
import shutil
import tarfile
from pathlib import Path

from databricks.sdk import WorkspaceClient

target = Path("/tmp/valhalla")
archive = Path("/tmp/valhalla-runtime.tar.gz")
shutil.rmtree(target, ignore_errors=True)
target.mkdir(parents=True)

volume_path = os.environ["VALHALLA_VOLUME_PATH"].rstrip("/")
download = WorkspaceClient().files.download(f"{volume_path}/runtime.tar.gz")
with archive.open("wb") as output:
    shutil.copyfileobj(download.contents, output)

with tarfile.open(archive, "r:gz") as bundle:
    root = target.resolve()
    for member in bundle.getmembers():
        if not (root / member.name).resolve().is_relative_to(root):
            raise RuntimeError(f"unsafe archive member: {member.name}")
    bundle.extractall(target)

(target / "bin/valhalla_service").chmod(0o755)
print(f"Downloaded and extracted {archive.stat().st_size} bytes from {volume_path}")
