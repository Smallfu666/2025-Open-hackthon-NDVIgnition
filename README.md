

## Overview
**NDVIgnition** integrates **Hierarchical Localization (HLOC)** with **WebODM** to build a GPU-accelerated aerial photogrammetry pipeline.  
It replaces WebODM’s CPU-based OpenSfM stage with a faster HLOC + COLMAP backend, enabling rapid 3D reconstruction and vegetation index (NDVI) analysis.

---

## Architecture


Drone Images → HLOC (SuperPoint + LightGlue) → COLMAP SfM → WebODM Visualization


---

## Docker Images
| Image | Description |
|-------|-------------|
| \project-hloc:hybrid\ | GPU-accelerated HLOC (PyTorch + LightGlue + COLMAP) |
| \project-webodm:latest\ | Modified WebODM with COLMAP ingestion |
| \opendronemap/nodeodm:gpu\ | WebODM GPU node for final reconstruction |
```
docker pull nick20350/ndvignation-hloc:hybrid
docker pull nick20350/ndvignation-webodm:latest
```
---

## Quick Start

### 1️⃣ Feature Extraction + Matching
```
docker run --rm --gpus all \
  -v "$(pwd)/images:/images:ro" \
  -v "$(pwd)/shared:/shared" \
  -v "$(pwd)/scripts:/workspace/scripts:ro" \
  project-hloc:hybrid \
  --images /images --out /shared/run_001 --batch-size 8
```

### 2️⃣ Sparse Reconstruction (COLMAP)

```
docker run --rm --gpus all \
  -v "$(pwd)/images:/images:ro" \
  -v "$(pwd)/shared:/shared" \
  --entrypoint python project-hloc:hybrid \
  -m hloc.reconstruction.main \
  --sfm-tool colmap \
  --features /shared/run_001/feats_superpoint.h5 \
  --matches /shared/run_001/matches.h5 \
  --pairs /shared/run_001/pairs-exhaustive.txt \
  --output /shared/run_001/sparse \
  --database /shared/run_001/colmap.db
```

### 3️⃣ Import to WebODM

```
docker run --rm \
  -v "$(pwd)/shared:/shared" \
  -v "$(pwd)/images:/images:ro" \
  project-webodm:latest \
  python /webodm/scripts/ingest_colmap.py \
  --model /shared/run_001/sparse/0 \
  --images_root /images \
  --out /webodm/app/media/hloc_run_001
```

