# Valhalla Databricks App proof of concept

This FastAPI service runs a precompiled `valhalla_service` subprocess on localhost and
exposes `POST /matrix` and `POST /augment-matrix`. A one-time Databricks job places an Andorra tile extract
and a relocatable Valhalla runtime in a Unity Catalog Volume resource.
At startup the App service principal downloads the archive through the Files API and
extracts it under ephemeral `/tmp`; Databricks Apps do not FUSE-mount UC Volumes.

Example body:

```json
{"new_point":{"lat":42.5063,"lon":1.5218},"existing_points":[{"lat":42.5078,"lon":1.5211}],"costing":"auto"}
```

The response contains both the new row (`from_new`) and new column (`to_new`) because
road travel times need not be symmetric.

For a complete solver matrix, send points in node-index order:

```json
{"points":[{"lat":42.5063,"lon":1.5218},{"lat":42.5078,"lon":1.5211}],"costing":"auto"}
```

`POST /matrix` returns Valhalla's directed `sources_to_targets` cells in the same row
and column order. Each cell includes `time` in seconds and `distance` in kilometers;
unreachable cells include Valhalla's error status. The endpoint accepts 2–500 points.

`build_valhalla.py` compiles Valhalla 3.5.1 and builds the Andorra tiles on DBR 15.4
LTS. `package_runtime.py` adds the full shared-library closure and regenerates the
archive when the runtime is rebuilt.

## Setup

1. Create a managed Unity Catalog Volume.
2. Run `build_valhalla.py` as a notebook task on DBR 15.4 LTS dedicated compute. Set
   `VOLUME_PATH` to `/Volumes/<catalog>/<schema>/<volume>`.
3. Run `package_runtime.py` on the same DBR version and Volume.
4. Create a Databricks App with a Volume resource named `valhalla-assets` and grant it
   `READ_VOLUME`.
5. Deploy this directory as the App source.

No workspace URL, user identity, credential, or resource identifier is stored in this
repository. The App uses its managed service-principal identity at runtime.
