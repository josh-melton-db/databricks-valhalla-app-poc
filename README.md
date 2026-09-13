# Valhalla Databricks App proof of concept

This FastAPI service runs a precompiled `valhalla_service` subprocess on localhost and
exposes `POST /matrix` and `POST /augment-matrix`. A Databricks job places a shared
Valhalla engine and independently selectable regional tile archives in a Unity Catalog
Volume. At startup the App service principal reads the manifest and downloads the
configured region through the Files API, then
extracts it under ephemeral `/tmp`; Databricks Apps do not FUSE-mount UC Volumes.

Example body:

```json
{"new_point":{"lat":42.3314,"lon":-83.0458},"existing_points":[{"lat":42.9634,"lon":-85.6681}],"costing":"auto"}
```

The response contains both the new row (`from_new`) and new column (`to_new`) because
road travel times need not be symmetric.

For a complete solver matrix, send points in node-index order:

```json
{"points":[{"lat":42.3314,"lon":-83.0458},{"lat":42.9634,"lon":-85.6681}],"costing":"auto"}
```

`POST /matrix` returns Valhalla's directed `sources_to_targets` cells in the same row
and column order. Each cell includes `time` in seconds and `distance` in kilometers;
unreachable cells include Valhalla's error status. The endpoint accepts 2–500 points.
The regional build raises Valhalla's automobile, taxi, and truck limits to 250,000
matrix pairs and 1,000 km per pair; production workloads should still be benchmarked
well below that request ceiling.

`build_valhalla.py` compiles Valhalla 3.5.1 and builds a named region on DBR 15.4 LTS.
The default parameters build Michigan from Geofabrik. The Volume layout is:

```text
manifest.json
engine/valhalla-3.5.1/runtime.tar.gz
regions/michigan/region.tar.gz
```

Additional regions can be published by rerunning the job with another safe `REGION_ID`
and HTTPS `PBF_URL`. Existing region entries remain in the manifest, and a validated
engine archive is preserved during regional refreshes.
`publish_compatible_engine.py` can republish the engine-only archive from a previously
validated DBR 15.4 `runtime/bin` and `runtime/lib` tree without rebuilding map tiles.

## Setup

1. Create a managed Unity Catalog Volume.
2. Run `build_valhalla.py` as a notebook task on DBR 15.4 LTS dedicated compute. Set
   `VOLUME_PATH`, `REGION_ID`, and `PBF_URL`.
3. Create a Databricks App with a Volume resource named `valhalla-assets` and grant it
   `READ_VOLUME`.
4. Set `VALHALLA_REGION` in `app.yaml` and deploy this directory as the App source.

No workspace URL, user identity, credential, or resource identifier is stored in this
repository. The App uses its managed service-principal identity at runtime.
