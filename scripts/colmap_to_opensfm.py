import argparse, json, os, shutil
from pathlib import Path
import exifread

def read_rows(p):
    out=[]; 
    for line in open(p,"r",errors="ignore"):
        line=line.strip()
        if not line or line.startswith("#"): continue
        out.append(line)
    return out

def parse_cameras(p):
    cams={}
    for line in read_rows(p):
        s=line.split()
        cid=int(s[0]); model=s[1]; w=int(s[2]); h=int(s[3]); prm=list(map(float,s[4:]))
        if model.startswith("PINHOLE"):
            fx,fy,cx,cy = prm[0],prm[1],prm[2],prm[3]
        else:
            fx=fy=prm[0]; cx=prm[2]; cy=prm[3]
        cams[cid]={"width":w,"height":h,"fx":fx,"fy":fy,"cx":cx,"cy":cy}
    return cams

def parse_images(p):
    shots={}; id2name={}
    for line in read_rows(p):
        s=line.split()
        if len(s)<10: continue
        iid=int(s[0]); qw,qx,qy,qz=map(float,s[1:5]); tx,ty,tz=map(float,s[5:8]); cid=int(s[8]); name=s[9]
        shots[name]={"camera_id":cid,"rotation":[qw,qx,qy,qz],"translation":[tx,ty,tz]}
        id2name[iid]=name
    return shots,id2name

def parse_points(p, id2name):
    pts=[]
    for line in read_rows(p):
        s=line.split()
        X,Y,Z=map(float,s[1:4]); R,G,B=map(int,s[4:7])
        tr=s[8:]; obs=[]
        for i in range(0,len(tr),2):
            iid=int(tr[i])
            if iid in id2name: obs.append({"shot_id":id2name[iid]})
        pts.append({"coordinates":[X,Y,Z],"color":[R,G,B],"observations":obs})
    return pts

def exif_to_json(img):
    exif={}
    try:
        with open(img,"rb") as f: tags=exifread.process_file(f, details=False)
        if "EXIF FocalLength" in tags:
            v=str(tags["EXIF FocalLength"])
            exif["focal_ratio"]=float(v.split("/")[0]) if "/" in v else float(v)
        if "GPS GPSLatitude" in tags and "GPS GPSLongitude" in tags:
            def dms(v): 
                vals=[x.num/x.den for x in v.values]; return vals[0]+vals[1]/60+vals[2]/3600
            lat=dms(tags["GPS GPSLatitude"]); lon=dms(tags["GPS GPSLongitude"])
            if str(tags.get("GPS GPSLatitudeRef","N"))=="S": lat=-lat
            if str(tags.get("GPS GPSLongitudeRef","E"))=="W": lon=-lon
            exif["gps"]={"latitude":lat,"longitude":lon}
    except Exception: pass
    return exif

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--colmap", required=True)   # sparse/0
    ap.add_argument("--images", required=True)   # rgb images dir
    ap.add_argument("--task", required=True)
    ap.add_argument("--out_root", default="/webodm/app/media")
    args=ap.parse_args()

    sparse=Path(args.colmap); imgs=Path(args.images)
    task_dir=Path(args.out_root)/args.task; osfs=task_dir/"opensfm"
    (osfs/"images").mkdir(parents=True, exist_ok=True)
    (osfs/"exif").mkdir(exist_ok=True)

    cams=parse_cameras(sparse/"cameras.txt")
    shots,id2name=parse_images(sparse/"images.txt")
    points=parse_points(sparse/"points3D.txt", id2name)

    # copy/link images + exif json
    for p in imgs.glob("*"):
        if not p.is_file(): continue
        dst=osfs/"images"/p.name
        try: os.link(p,dst)
        except Exception:
            shutil.copy2(p,dst)
        (osfs/"exif"/(p.stem+".json")).write_text(json.dumps(exif_to_json(p)))

    cam_models={}
    for cid,c in cams.items():
        cam_models[str(cid)]={"width":c["width"],"height":c["height"],
                              "focal_x":c["fx"],"focal_y":c["fy"],
                              "principal_x":c["cx"],"principal_y":c["cy"],
                              "k1":0.0,"k2":0.0,"p1":0.0,"p2":0.0}

    shots_out={name:{"camera":str(s["camera_id"]),
                     "rotation":s["rotation"],
                     "translation":s["translation"]} for name,s in shots.items()}

    recon=[{"cameras":cam_models,"shots":shots_out,"points":points}]
    (osfs/"reconstruction.json").write_text(json.dumps(recon))
    print("✅ OpenSfM structure ready at", osfs)

if __name__=="__main__":
    main()
