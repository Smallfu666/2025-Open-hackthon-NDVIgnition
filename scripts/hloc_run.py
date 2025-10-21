#!/usr/bin/env python3
import argparse, os, shutil, sys
from pathlib import Path
import torch
from hloc import extract_features as ef, match_features as mf, pairs_from_exhaustive, reconstruction

def main():
    ap = argparse.ArgumentParser(description="HLOC full pipeline (v1.3+ API compatible)")
    ap.add_argument("--images", required=True, help="影像資料夾 (.jpg/.jpeg/.png)")
    ap.add_argument("--out", required=True, help="輸出資料夾 (自動建立 images/, feats/, matches/, sparse/)")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--matcher", default="lightglue", choices=["lightglue", "NN-superpoint"])
    args = ap.parse_args()

    images = Path(args.images)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # ---------- 1️⃣ 收集影像 ----------
    rgb = out / "images"
    rgb.mkdir(exist_ok=True)
    exts = [".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"]
    kept = 0
    for p in sorted(images.rglob("*")):
        if p.is_file() and p.suffix in exts:
            dst = rgb / p.name
            if not dst.exists():
                try:
                    os.link(p, dst)
                except Exception:
                    shutil.copy2(p, dst)
            kept += 1
    if kept == 0:
        print(f"[HLOC] ❌ No images found under {images}", file=sys.stderr)
        sys.exit(2)
    print(f"[HLOC] Collected {kept} images -> {rgb}")

    # ---------- 2️⃣ 特徵提取 ----------
    feat_conf = ef.confs.get("superpoint_max") or ef.confs.get("superpoint_inloc")
    feats = out / "feats_superpoint"
    print(f"[HLOC] Extracting features -> {feats}")
    ef.main(feat_conf, rgb, feats)

    # ---------- 3️⃣ 自動配對 ----------
    pairs = out / "pairs-exhaustive.txt"
    print(f"[HLOC] Generating exhaustive pairs -> {pairs}")
    pairs_from_exhaustive.main(rgb, pairs)

    # ---------- 4️⃣ 特徵匹配 ----------
    matcher_conf = mf.confs.get(args.matcher) or mf.confs.get("NN-superpoint")
    matches = out / f"matches_{args.matcher}"
    print(f"[HLOC] Matching features ({args.matcher}) -> {matches}")
    mf.main(matcher_conf, pairs, feats, matches)

    # ---------- 5️⃣ COLMAP 重建 ----------
    sparse = out / "sparse"
    print(f"[HLOC] Running COLMAP reconstruction -> {sparse}")
    reconstruction.main(rgb, pairs, feats, matches, sparse)

    print(f"✅ Done! Sparse model saved at: {sparse}")

if __name__ == "__main__":
    if not torch.cuda.is_available():
        print("[HLOC] ⚠️ CUDA not available, using CPU")
    main()
