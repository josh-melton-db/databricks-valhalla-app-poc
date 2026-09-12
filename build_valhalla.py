# Databricks notebook source
dbutils.widgets.text("VOLUME_PATH", "")
dbutils.widgets.text("PBF_URL", "https://download.geofabrik.de/europe/andorra-latest.osm.pbf")

import os

volume_path = dbutils.widgets.get("VOLUME_PATH").rstrip("/")
pbf_url = dbutils.widgets.get("PBF_URL")
if not volume_path.startswith("/Volumes/"):
    raise ValueError("VOLUME_PATH must be /Volumes/<catalog>/<schema>/<volume>")
os.environ["VALHALLA_VOLUME_PATH"] = volume_path
os.environ["VALHALLA_PBF_URL"] = pbf_url

# COMMAND ----------

# MAGIC %sh
# MAGIC set -euxo pipefail
# MAGIC sudo apt-get update -qq
# MAGIC sudo apt-get install -y -qq git cmake make g++ jq wget rsync
# MAGIC rm -rf /local_disk0/valhalla-poc
# MAGIC git clone --depth 1 --branch 3.5.1 --recurse-submodules --shallow-submodules https://github.com/valhalla/valhalla.git /local_disk0/valhalla-poc
# MAGIC cd /local_disk0/valhalla-poc
# MAGIC ./scripts/install-linux-deps.sh
# MAGIC cmake -B build -DCMAKE_BUILD_TYPE=Release -DENABLE_PYTHON_BINDINGS=OFF -DENABLE_TESTS=OFF -DENABLE_BENCHMARKS=OFF
# MAGIC cmake --build build --parallel 16
# MAGIC sudo cmake --install build
# MAGIC sudo ldconfig

# COMMAND ----------

# MAGIC %sh
# MAGIC set -euxo pipefail
# MAGIC work=/local_disk0/valhalla-runtime
# MAGIC rm -rf "$work"
# MAGIC mkdir -p "$work/tiles" "$work/bin" "$work/lib"
# MAGIC pbf="$work/andorra.osm.pbf"
# MAGIC wget -q -O "$pbf" "${VALHALLA_PBF_URL:?}"
# MAGIC valhalla_build_config \
# MAGIC   --mjolnir-tile-dir "$work/tiles" \
# MAGIC   --mjolnir-tile-extract "$work/tiles/tiles.tar" \
# MAGIC   --mjolnir-timezone "$work/tiles/timezones.sqlite" \
# MAGIC   --mjolnir-admin "$work/tiles/admins.sqlite" > "$work/tiles/valhalla.build.json"
# MAGIC valhalla_build_timezones > "$work/tiles/timezones.sqlite"
# MAGIC valhalla_build_admins -c "$work/tiles/valhalla.build.json" "$pbf"
# MAGIC valhalla_build_tiles -c "$work/tiles/valhalla.build.json" "$pbf"
# MAGIC valhalla_build_extract -c "$work/tiles/valhalla.build.json" -v
# MAGIC jq --arg from "$work/tiles" --arg to "/tmp/valhalla/tiles" \
# MAGIC   'walk(if type == "string" and startswith($from) then $to + (.[($from|length):]) else . end)' \
# MAGIC   "$work/tiles/valhalla.build.json" > "$work/tiles/valhalla.json"
# MAGIC rm "$work/tiles/valhalla.build.json" "$pbf"
# MAGIC cp /usr/local/bin/valhalla_service "$work/bin/"
# MAGIC ldd /usr/local/bin/valhalla_service | awk '/=> \/|^\s*\// {for(i=1;i<=NF;i++) if ($i ~ /^\//) print $i}' | sort -u | while read -r lib; do
# MAGIC   case "$lib" in
# MAGIC     */libc.so.*|*/libm.so.*|*/libpthread.so.*|*/libdl.so.*|*/librt.so.*|*/ld-linux-*.so.*) ;;
# MAGIC     *) cp -L "$lib" "$work/lib/" ;;
# MAGIC   esac
# MAGIC done
# MAGIC destination="${VALHALLA_VOLUME_PATH:?}/runtime"
# MAGIC rm -rf "$destination"
# MAGIC mkdir -p "$destination"
# MAGIC rsync -a "$work/" "$destination/"
# MAGIC tar -C "$work" -czf "${VALHALLA_VOLUME_PATH:?}/runtime.tar.gz" .
# MAGIC du -sh "$destination"

# COMMAND ----------

runtime_path = f"{volume_path}/runtime"
assert os.path.exists(f"{runtime_path}/bin/valhalla_service")
assert os.path.exists(f"{runtime_path}/tiles/tiles.tar")
print(f"Valhalla App runtime ready at {runtime_path}")
