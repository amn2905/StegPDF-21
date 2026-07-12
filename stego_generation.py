import os
import csv
import time
import shutil
import random
import hashlib
import traceback
import multiprocessing as mp
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple
from collections import Counter

from tqdm import tqdm
import numpy as np

import pikepdf
import fitz  # PyMuPDF
from PIL import Image
import io
import base64


# ============================================================
# CONFIG
# ============================================================

@dataclass
class Config:
    clean_dir: Path = Path(r"D:\CLEAN_PDFS")         # <-- CHANGE THIS
    start_id: int = 1
    end_id: int = 10000
    clean_name_fmt: str = "{:05d}.pdf"

    out_root: Path = Path(r"E:\PDF_STEGO_DATASET")   # <-- CHANGE THIS

    dataset_full_dirname: str = "dataset_full"
    splits_dirname: str = "splits"
    logs_dirname: str = "logs"
    tmp_dirname: str = "_tmp"

    variations: Dict[str, int] = None
    techniques: List[str] = None

    workers: int = 6
    retries: int = 2

    verify_pdf: bool = True
    compute_sha256: bool = False

    split_seed: int = 2026
    train_ratio: float = 0.80
    val_ratio: float = 0.10
    test_ratio: float = 0.10


def make_config() -> Config:
    cfg = Config()
    cfg.techniques = [f"T{str(i).zfill(2)}" for i in range(1, 9)]
    cfg.variations = {"v1": 256, "v2": 2048, "v3": 16384}
    return cfg


# ============================================================
# UTILS
# ============================================================

def now_iso() -> str:
    return datetime.utcnow().isoformat()

def safe_mkdir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def is_probably_pdf(path: Path) -> bool:
    try:
        if not path.exists() or path.stat().st_size < 100:
            return False
        with open(path, "rb") as f:
            head = f.read(8)
        return head.startswith(b"%PDF")
    except Exception:
        return False

def verify_pdf_open(path: Path) -> bool:
    try:
        with pikepdf.open(path):
            return True
    except Exception:
        return False

def safe_move(tmp_out: Path, out_final: Path):
    safe_mkdir(out_final.parent)
    if out_final.exists():
        out_final.unlink()
    shutil.move(str(tmp_out), str(out_final))

def append_csv(csv_path: Path, header: List[str], row: Dict[str, Any]):
    exists = csv_path.exists()
    safe_mkdir(csv_path.parent)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if not exists:
            w.writeheader()
        w.writerow(row)

def write_csv(csv_path: Path, header: List[str], rows: List[Dict[str, Any]]):
    safe_mkdir(csv_path.parent)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def b64(payload: bytes) -> str:
    return base64.b64encode(payload).decode("ascii")

def build_payload(source_id: int, technique: str, variant: str, payload_bytes: int, seed: int) -> bytes:
    rnd = random.Random(seed)
    header = f"MAGIC:STEG|SRC:{source_id:05d}|{technique}|{variant}|SIZE:{payload_bytes}|SEED:{seed}\n".encode("utf-8")
    remain = max(0, payload_bytes - len(header))
    body = bytes(rnd.getrandbits(8) for _ in range(remain))
    return header + body

def bits_from_bytes(data: bytes) -> List[int]:
    out = []
    for b in data:
        for i in range(8):
            out.append((b >> (7 - i)) & 1)
    return out


# ============================================================
# PATHS
# ============================================================

def root_dataset(cfg: Config) -> Path:
    return cfg.out_root / cfg.dataset_full_dirname

def root_clean(cfg: Config) -> Path:
    return root_dataset(cfg) / "clean"

def root_stego(cfg: Config) -> Path:
    return root_dataset(cfg) / "stego"

def log_dir(cfg: Config) -> Path:
    return cfg.out_root / cfg.logs_dirname

def tmp_dir(cfg: Config) -> Path:
    return cfg.out_root / cfg.tmp_dirname

def splits_root(cfg: Config) -> Path:
    return cfg.out_root / cfg.splits_dirname

def clean_out_path(cfg: Config, sid: int) -> Path:
    return root_clean(cfg) / cfg.clean_name_fmt.format(sid)

def stego_out_path(cfg: Config, sid: int, tech: str, var: str) -> Path:
    fname = f"{sid:05d}__{tech}__{var}.pdf"
    return root_stego(cfg) / tech / var / fname


# ============================================================
# TECHNIQUES (8)
# ============================================================

def T01_metadata(clean_pdf: Path, tmp_out: Path, payload: bytes, seed: int, cfg: Config):
    payload_b64 = b64(payload)
    with pikepdf.open(clean_pdf) as pdf:
        info = pdf.docinfo
        info["/Title"] = pikepdf.String("Document")
        info["/Author"] = pikepdf.String("System")
        info["/Keywords"] = pikepdf.String(payload_b64[:250])

        xmp = f"""<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description rdf:about="" xmlns:steg="http://steganalysis.local/ns/">
<steg:payload>{payload_b64}</steg:payload>
</rdf:Description>
</rdf:RDF>
</x:xmpmeta>"""
        pdf.Root["/Metadata"] = pdf.make_stream(xmp.encode("utf-8"))
        pdf.save(tmp_out)

def T02_invisible_white_text(clean_pdf: Path, tmp_out: Path, payload: bytes, seed: int, cfg: Config):
    payload_b64 = b64(payload)
    doc = fitz.open(clean_pdf)
    if doc.page_count < 1:
        raise RuntimeError("No pages")
    page = doc[0]
    rect = page.rect
    page.insert_text(
        fitz.Point(rect.x1 - 50, rect.y1 - 10),
        payload_b64[:2000],
        fontsize=1,
        color=(1, 1, 1),
        overlay=True
    )
    doc.save(tmp_out)
    doc.close()

def T03_text_spacing(clean_pdf: Path, tmp_out: Path, payload: bytes, seed: int, cfg: Config):
    bits = bits_from_bytes(payload)[:2500]
    tokens = ["A" + ("  " if b else " ") + "B" for b in bits]
    encoded = " ".join(tokens)

    doc = fitz.open(clean_pdf)
    if doc.page_count < 1:
        raise RuntimeError("No pages")
    page = doc[0]
    rect = page.rect
    page.insert_text(
        fitz.Point(20, rect.y1 - 20),
        encoded[:4000],
        fontsize=3,
        color=(0.95, 0.95, 0.95),
        overlay=True
    )
    doc.save(tmp_out)
    doc.close()

def T04_zero_width_unicode(clean_pdf: Path, tmp_out: Path, payload: bytes, seed: int, cfg: Config):
    bits = bits_from_bytes(payload)[:8000]
    ZWSP = "\u200B"
    ZWJ = "\u200D"
    ZWNJ = "\u200C"
    chars = []
    for i, b in enumerate(bits):
        chars.append(ZWJ if b else ZWSP)
        if i % 64 == 63:
            chars.append(ZWNJ)
    zw = "".join(chars)

    doc = fitz.open(clean_pdf)
    if doc.page_count < 1:
        raise RuntimeError("No pages")
    page = doc[0]
    rect = page.rect
    page.insert_text(
        fitz.Point(30, rect.y1 - 10),
        zw,
        fontsize=1,
        color=(0, 0, 0),
        overlay=True
    )
    doc.save(tmp_out)
    doc.close()

def T05_pdf_comments(clean_pdf: Path, tmp_out: Path, payload: bytes, seed: int, cfg: Config):
    payload_b64 = b64(payload)
    raw = clean_pdf.read_bytes()
    if not raw.startswith(b"%PDF"):
        raise RuntimeError("Not a PDF")
    head, rest = raw.split(b"\n", 1) if b"\n" in raw else (raw, b"")
    comment = (b"%STEG_COMMENT:" + payload_b64.encode("ascii") + b"\n")[:20000]
    tmp_out.write_bytes(head + b"\n" + comment + rest)

def T06_unused_indirect_objects(clean_pdf: Path, tmp_out: Path, payload: bytes, seed: int, cfg: Config):
    with pikepdf.open(clean_pdf) as pdf:
        stream = pdf.make_stream(payload)
        _ = pdf.make_indirect(stream)
        pdf.save(tmp_out)

def T07_stream_padding(clean_pdf: Path, tmp_out: Path, payload: bytes, seed: int, cfg: Config):
    with pikepdf.open(clean_pdf) as pdf:
        done = False
        for obj in pdf.objects:
            try:
                if isinstance(obj, pikepdf.Stream):
                    data = obj.read_bytes()
                    pad = b"\nJUNK_BEGIN\n" + payload[:20000] + b"\nJUNK_END\n"
                    obj.write(data + pad)
                    done = True
                    break
            except Exception:
                continue
        if not done:
            stream = pdf.make_stream(b"PAD:" + payload[:20000])
            _ = pdf.make_indirect(stream)
        pdf.save(tmp_out)

def lsb_embed_rgb(img: Image.Image, payload: bytes, seed: int) -> Image.Image:
    img = img.convert("RGB")
    arr = np.array(img)
    h, w, _ = arr.shape

    bits = bits_from_bytes(payload)
    length_bits = [(len(bits) >> (31 - i)) & 1 for i in range(32)]
    full = length_bits + bits

    cap = h * w * 3
    if len(full) > cap:
        raise RuntimeError(f"Payload too big for image LSB. Need={len(full)} cap={cap}")

    positions = list(range(cap))
    rnd = random.Random(seed)
    rnd.shuffle(positions)
    positions = positions[:len(full)]

    flat = arr.reshape(-1)
    for pos, bit in zip(positions, full):
        flat[pos] = (flat[pos] & 0xFE) | bit

    out = flat.reshape(arr.shape).astype(np.uint8)
    return Image.fromarray(out, mode="RGB")

def T08_image_stego(clean_pdf: Path, tmp_out: Path, payload: bytes, seed: int, cfg: Config):
    doc = fitz.open(clean_pdf)
    xref = None
    for pi in range(min(doc.page_count, 5)):
        imgs = doc[pi].get_images(full=True)
        if imgs:
            xref = imgs[0][0]
            break
    if xref is None:
        doc.close()
        raise RuntimeError("No embedded images found")

    base = doc.extract_image(xref)
    img_bytes = base["image"]

    pil = Image.open(io.BytesIO(img_bytes))
    stego = lsb_embed_rgb(pil, payload, seed=seed)

    buf = io.BytesIO()
    stego.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    doc.update_stream(xref, png_bytes)
    doc.save(tmp_out)
    doc.close()


TECHNIQUE_FUNCS = {
    "T01": T01_metadata,
    "T02": T02_invisible_white_text,
    "T03": T03_text_spacing,
    "T04": T04_zero_width_unicode,
    "T05": T05_pdf_comments,
    "T06": T06_unused_indirect_objects,
    "T07": T07_stream_padding,
    "T08": T08_image_stego,
}


# ============================================================
# SPLIT (SOURCE-WISE)
# ============================================================

def build_source_splits(cfg: Config) -> Dict[str, List[int]]:
    ids = list(range(cfg.start_id, cfg.end_id + 1))
    rnd = random.Random(cfg.split_seed)
    rnd.shuffle(ids)

    n = len(ids)
    n_train = int(n * cfg.train_ratio)
    n_val = int(n * cfg.val_ratio)
    train_ids = ids[:n_train]
    val_ids = ids[n_train:n_train + n_val]
    test_ids = ids[n_train + n_val:]

    print(f"[+] Split: train={len(train_ids)}, val={len(val_ids)}, test={len(test_ids)}")
    return {"train": train_ids, "val": val_ids, "test": test_ids}


# ============================================================
# GENERATION
# ============================================================

def copy_clean(cfg: Config):
    safe_mkdir(root_clean(cfg))
    for sid in tqdm(range(cfg.start_id, cfg.end_id + 1), desc="Copy clean PDFs"):
        src = cfg.clean_dir / cfg.clean_name_fmt.format(sid)
        dst = clean_out_path(cfg, sid)
        if not src.exists():
            continue
        if dst.exists() and dst.stat().st_size == src.stat().st_size:
            continue
        shutil.copy2(src, dst)

def worker_generate(args: Tuple[int, str, str, Config]) -> Dict[str, Any]:
    sid, tech, var, cfg = args
    t0 = time.time()

    clean_pdf = clean_out_path(cfg, sid)
    out_pdf = stego_out_path(cfg, sid, tech, var)

    if out_pdf.exists() and is_probably_pdf(out_pdf):
        return {"status":"SKIP","source_id":sid,"technique":tech,"variant":var,"out_path":str(out_pdf),"time_sec":round(time.time()-t0,3)}

    if not clean_pdf.exists():
        return {"status":"FAIL","source_id":sid,"technique":tech,"variant":var,"fail_reason":"missing_clean","trace":"","time_sec":round(time.time()-t0,3)}

    payload_bytes = cfg.variations[var]
    seed = (sid * 1000003) ^ (hash(tech) & 0xFFFFFFFF) ^ (hash(var) & 0xFFFFFFFF)
    payload = build_payload(sid, tech, var, payload_bytes, seed)

    safe_mkdir(tmp_dir(cfg))
    tmp_out = tmp_dir(cfg) / f"{sid:05d}__{tech}__{var}__tmp.pdf"
    func = TECHNIQUE_FUNCS[tech]
    safe_mkdir(out_pdf.parent)

    for attempt in range(cfg.retries + 1):
        try:
            if tmp_out.exists():
                tmp_out.unlink()

            func(clean_pdf, tmp_out, payload, seed, cfg)

            if not tmp_out.exists():
                raise RuntimeError("No output generated")

            if cfg.verify_pdf and not verify_pdf_open(tmp_out):
                raise RuntimeError("Generated PDF failed verification")

            safe_move(tmp_out, out_pdf)

            return {
                "status": "SUCCESS",
                "source_id": sid,
                "technique": tech,
                "variant": var,
                "payload_bytes": payload_bytes,
                "seed": seed,
                "out_path": str(out_pdf),
                "sha256": sha256_file(out_pdf) if cfg.compute_sha256 else "",
                "time_sec": round(time.time() - t0, 3),
            }

        except Exception as e:
            if attempt < cfg.retries:
                time.sleep(0.25 * (attempt + 1))
                continue

            trace = traceback.format_exc()
            try:
                if tmp_out.exists():
                    tmp_out.unlink()
            except Exception:
                pass

            return {
                "status": "FAIL",
                "source_id": sid,
                "technique": tech,
                "variant": var,
                "fail_reason": f"{type(e).__name__}: {str(e)}",
                "trace": trace[-4000:],
                "time_sec": round(time.time() - t0, 3),
            }


def generate_all_stego(cfg: Config) -> Tuple[Path, Path]:
    safe_mkdir(log_dir(cfg))

    labels_full = log_dir(cfg) / "labels_full.csv"
    failures = log_dir(cfg) / "failures.csv"

    labels_header = ["created_at","label","source_id","file_path","technique","variant","payload_bytes","seed","sha256","status","time_sec"]
    fail_header = ["created_at","source_id","technique","variant","fail_reason","trace","time_sec"]

    tasks = []
    for sid in range(cfg.start_id, cfg.end_id + 1):
        for tech in cfg.techniques:
            for var in cfg.variations.keys():
                tasks.append((sid, tech, var, cfg))

    print(f"[+] Expected stego outputs = {len(tasks)}  (N * 8 * 3)")

    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=cfg.workers) as pool:
        for res in tqdm(pool.imap_unordered(worker_generate, tasks), total=len(tasks), desc="Generate stego"):
            sid = res["source_id"]
            tech = res["technique"]
            var = res["variant"]

            if res["status"] in ("SUCCESS","SKIP"):
                out_pdf = stego_out_path(cfg, sid, tech, var)
                append_csv(labels_full, labels_header, {
                    "created_at": now_iso(),
                    "label": "stego",
                    "source_id": f"{sid:05d}",
                    "file_path": str(out_pdf.relative_to(cfg.out_root)).replace("\\","/"),
                    "technique": tech,
                    "variant": var,
                    "payload_bytes": res.get("payload_bytes", cfg.variations[var]),
                    "seed": res.get("seed",""),
                    "sha256": res.get("sha256",""),
                    "status": res["status"],
                    "time_sec": res.get("time_sec",""),
                })
            else:
                append_csv(failures, fail_header, {
                    "created_at": now_iso(),
                    "source_id": f"{sid:05d}",
                    "technique": tech,
                    "variant": var,
                    "fail_reason": res.get("fail_reason",""),
                    "trace": res.get("trace",""),
                    "time_sec": res.get("time_sec",""),
                })

    print("[+] Stego generation finished.")
    return labels_full, failures


# ============================================================
# SPLIT EXPORT (TRAIN/VAL/TEST folders + CSV)
# ============================================================

def export_splits(cfg: Config, splits: Dict[str, List[int]]):
    """
    Creates:
      splits/train/clean + splits/train/stego
      splits/val/clean   + splits/val/stego
      splits/test/clean  + splits/test/stego

    Also writes:
      logs/train.csv, logs/val.csv, logs/test.csv
    """
    safe_mkdir(splits_root(cfg))

    csv_header = ["label","source_id","file_path","technique","variant","payload_bytes"]

    def export_one(split_name: str, ids: List[int], out_csv: Path):
        split_dir = splits_root(cfg) / split_name
        clean_dir = split_dir / "clean"
        stego_dir = split_dir / "stego"
        safe_mkdir(clean_dir)
        safe_mkdir(stego_dir)

        rows = []

        # clean
        for sid in tqdm(ids, desc=f"Export {split_name} clean"):
            src = clean_out_path(cfg, sid)
            if not src.exists():
                continue
            dst = clean_dir / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
            rows.append({
                "label":"clean",
                "source_id":f"{sid:05d}",
                "file_path":str(dst.relative_to(cfg.out_root)).replace("\\","/"),
                "technique":"NONE",
                "variant":"NONE",
                "payload_bytes":0
            })

        # stego
        for sid in tqdm(ids, desc=f"Export {split_name} stego"):
            for tech in cfg.techniques:
                for var, pbytes in cfg.variations.items():
                    src = stego_out_path(cfg, sid, tech, var)
                    if not src.exists():
                        continue
                    rel = src.relative_to(root_dataset(cfg))  # stego/Txx/vx/file.pdf
                    dst = stego_dir / rel
                    safe_mkdir(dst.parent)
                    if not dst.exists():
                        shutil.copy2(src, dst)
                    rows.append({
                        "label":"stego",
                        "source_id":f"{sid:05d}",
                        "file_path":str(dst.relative_to(cfg.out_root)).replace("\\","/"),
                        "technique":tech,
                        "variant":var,
                        "payload_bytes":pbytes
                    })

        write_csv(out_csv, csv_header, rows)

    export_one("train", splits["train"], log_dir(cfg)/"train.csv")
    export_one("val",   splits["val"],   log_dir(cfg)/"val.csv")
    export_one("test",  splits["test"],  log_dir(cfg)/"test.csv")

    print("[+] Split export finished.")
    print(f"    Train folder: {splits_root(cfg)/'train'}")
    print(f"    Val folder  : {splits_root(cfg)/'val'}")
    print(f"    Test folder : {splits_root(cfg)/'test'}")


# ============================================================
# REPORT GENERATOR
# ============================================================

def generate_reports(cfg: Config, labels_full_csv: Path, failures_csv: Path):
    print("\n[+] Generating reports...")

    total_expected = (cfg.end_id - cfg.start_id + 1) * len(cfg.techniques) * len(cfg.variations)

    tech_created = Counter()
    var_created = Counter()

    created = 0
    if labels_full_csv.exists():
        with open(labels_full_csv, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                if row.get("label") != "stego":
                    continue
                status = row.get("status")
                if status in ("SUCCESS", "SKIP"):
                    created += 1
                    tech_created[row["technique"]] += 1
                    var_created[row["variant"]] += 1

    fails = 0
    top_fail_sources = Counter()
    if failures_csv.exists():
        with open(failures_csv, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                fails += 1
                top_fail_sources[row.get("source_id", "UNKNOWN")] += 1

    report_summary = log_dir(cfg) / "report_summary.txt"
    report_tech = log_dir(cfg) / "report_technique.csv"
    report_var = log_dir(cfg) / "report_variant.csv"
    report_top = log_dir(cfg) / "report_top_failed_sources.csv"

    # technique report
    tech_rows = []
    expected_per_tech = (cfg.end_id - cfg.start_id + 1) * len(cfg.variations)
    for tech in cfg.techniques:
        ok = tech_created.get(tech, 0)
        pct = (ok / max(expected_per_tech, 1)) * 100
        tech_rows.append({"technique": tech, "expected": expected_per_tech, "created": ok, "success_pct": round(pct, 2)})
    write_csv(report_tech, ["technique","expected","created","success_pct"], tech_rows)

    # variant report
    var_rows = []
    expected_per_var = (cfg.end_id - cfg.start_id + 1) * len(cfg.techniques)
    for var in cfg.variations.keys():
        ok = var_created.get(var, 0)
        pct = (ok / max(expected_per_var, 1)) * 100
        var_rows.append({"variant": var, "expected": expected_per_var, "created": ok, "success_pct": round(pct, 2)})
    write_csv(report_var, ["variant","expected","created","success_pct"], var_rows)

    # top failed sources
    top_rows = [{"source_id": sid, "fail_count": c} for sid, c in top_fail_sources.most_common(50)]
    write_csv(report_top, ["source_id","fail_count"], top_rows)

    overall_pct = (created / max(total_expected, 1)) * 100
    with open(report_summary, "w", encoding="utf-8") as f:
        f.write("PDF STEGO DATASET REPORT\n")
        f.write("========================\n\n")
        f.write(f"Generated at (UTC): {now_iso()}\n")
        f.write(f"Expected outputs  : {total_expected}\n")
        f.write(f"Created outputs   : {created}\n")
        f.write(f"Failed outputs    : {fails}\n")
        f.write(f"Overall success % : {overall_pct:.2f}%\n\n")
        f.write("Top failed sources:\n")
        for sid, c in top_fail_sources.most_common(20):
            f.write(f"  {sid}.pdf -> {c} failures\n")

    print("[+] Reports ready in logs/.")


# ============================================================
# MAIN
# ============================================================

def main():
    cfg = make_config()

    print("\n====================================")
    print(" MASTER PDF STEGO DATASET BUILDER")
    print("====================================\n")
    print(f"Clean dir : {cfg.clean_dir}")
    print(f"Out root  : {cfg.out_root}")
    print(f"Range     : {cfg.start_id:05d} - {cfg.end_id:05d}")
    print(f"Workers   : {cfg.workers}")
    print(f"Techniques: {cfg.techniques}")
    print(f"Variations: {cfg.variations}")
    print("")

    safe_mkdir(cfg.out_root)
    safe_mkdir(root_dataset(cfg))
    safe_mkdir(root_clean(cfg))
    safe_mkdir(root_stego(cfg))
    safe_mkdir(log_dir(cfg))
    safe_mkdir(tmp_dir(cfg))
    safe_mkdir(splits_root(cfg))

    # 1) Copy clean -> dataset_full/clean
    copy_clean(cfg)

    # 2) Build split ids (source-wise)
    splits = build_source_splits(cfg)

    # 3) Generate full stego dataset (equal distribution)
    labels_full_csv, failures_csv = generate_all_stego(cfg)

    # 4) Export train/val/test folders + CSV
    export_splits(cfg, splits)

    # 5) Reports
    generate_reports(cfg, labels_full_csv, failures_csv)

    print("\n✅ COMPLETE: dataset_full + splits(train/val/test) + logs ready.\n")
    print(f"Full dataset : {root_dataset(cfg)}")
    print(f"Splits       : {splits_root(cfg)}")
    print(f"Logs         : {log_dir(cfg)}\n")


if __name__ == "__main__":
    mp.freeze_support()
    main()