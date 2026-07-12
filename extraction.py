import os
import csv
import math
import logging
import warnings
from collections import Counter
from multiprocessing import Process, Queue

import pikepdf
from PyPDF2 import PdfReader

warnings.filterwarnings("ignore")

# ================= USER SETTINGS =================
CHUNK_SIZE = 2000                 # PDFs per run
PDF_TIMEOUT_SECONDS = 8
TEXT_CHAR_LIMIT = 30000

SPLITS = ["train", "test", "val"]
CLASSES = ["clean", "stego"]

# ================= PATHS =================
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CSV_PATH = os.path.join(OUTPUT_DIR, "features_25_FINAL.csv")
LOG_PATH = os.path.join(OUTPUT_DIR, "extraction.log")
PROGRESS_PATH = os.path.join(OUTPUT_DIR, "progress.txt")

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# ================= PROGRESS =================
def load_progress():
    if not os.path.exists(PROGRESS_PATH):
        return set()
    with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def save_progress(key):
    with open(PROGRESS_PATH, "a", encoding="utf-8") as f:
        f.write(key + "\n")

# ================= CSV SAFE APPEND =================
def safe_append_csv(path, row):
    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

# ================= UTILS =================
def entropy(data: bytes):
    if not data:
        return 0.0
    freq = Counter(data)
    total = len(data)
    return -sum((c / total) * math.log2(c / total) for c in freq.values())


def safe_text(reader, limit):
    out, total = [], 0
    for p in reader.pages:
        if total >= limit:
            break
        try:
            t = p.extract_text()
            if not t:
                continue
            remain = limit - total
            out.append(t[:remain])
            total += len(t[:remain])
        except Exception:
            continue
    return "".join(out)

# ================= WORKER =================
def _extract_worker(pdf_path, q):
    try:
        with open(pdf_path, "rb") as f:
            raw = f.read()

        reader = PdfReader(pdf_path, strict=False)
        if reader.is_encrypted:
            q.put(None)
            return

        text = safe_text(reader, TEXT_CHAR_LIMIT)
        metadata = reader.metadata or {}
        pages = len(reader.pages)

        with pikepdf.open(pdf_path) as pdf:
            object_count = len(pdf.objects)

        raw_len = max(len(raw), 1)
        tl = max(len(text), 1)
        zw = {8203, 8204, 8205}

        f = {
            "file_size": raw_len,
            "page_count": pages,
            "object_count": object_count,
            "avg_objects_per_page": object_count / max(pages, 1),
        }

        orphan = max(object_count - pages * 5, 0)
        f["orphan_object_count"] = orphan
        f["orphan_object_depth"] = orphan / max(object_count, 1)
        f["unused_object_ratio"] = f["orphan_object_depth"]

        mv = "".join(str(v) for v in metadata.values()).encode(errors="ignore")
        f["metadata_length"] = len(mv)
        f["metadata_key_count"] = len(metadata)
        f["custom_metadata_key_count"] = sum(
            1 for k in metadata if not str(k).lower().startswith("/producer")
        )
        f["metadata_value_entropy"] = entropy(mv)

        f["zero_width_unicode_density"] = sum(1 for c in text if ord(c) in zw) / tl
        f["invisible_text_ratio"] = sum(1 for c in text if c.isspace()) / tl
        f["avg_char_spacing_deviation"] = len(set(text)) / tl
        f["whitespace_run_variance"] = text.count("   ") / tl

        f["comment_object_count"] = raw.count(b"%")
        f["comment_length_ratio"] = f["comment_object_count"] / raw_len
        f["xref_gap_score"] = raw.count(b"xref")
        f["padding_byte_ratio"] = raw.count(b"\x00") / raw_len

        f["image_count"] = raw.count(b"/Image")
        f["image_entropy_delta"] = entropy(raw[:12000])
        f["image_size_anomaly"] = f["image_count"] / max(pages, 1)

        f["page_object_distribution_entropy"] = entropy(str(object_count).encode())
        f["text_to_nontext_ratio"] = tl / raw_len
        f["structural_complexity_score"] = object_count * pages

        q.put(f)

    except Exception:
        q.put(None)

# ================= MAIN =================
def main():
    completed = load_progress()
    processed_this_run = 0
    skipped = 0

    for split in SPLITS:
        for cls in CLASSES:
            folder = os.path.join(split, cls)
            if not os.path.isdir(folder):
                continue

            for pdf in sorted(os.listdir(folder)):
                if processed_this_run >= CHUNK_SIZE:
                    break

                if not pdf.lower().endswith(".pdf"):
                    continue

                key = f"{split}|{cls}|{pdf}"
                if key in completed:
                    continue

                q = Queue()
                p = Process(
                    target=_extract_worker,
                    args=(os.path.join(folder, pdf), q)
                )

                p.start()
                p.join(PDF_TIMEOUT_SECONDS)

                if p.is_alive():
                    p.terminate()
                    p.join()
                    skipped += 1
                    continue

                if q.empty():
                    skipped += 1
                    continue

                feats = q.get()
                if feats is None:
                    skipped += 1
                    continue

                feats["split"] = split
                feats["file"] = cls
                feats["filename"] = pdf

                safe_append_csv(CSV_PATH, feats)
                save_progress(key)

                processed_this_run += 1

                if processed_this_run % 100 == 0:
                    logging.info(
                        f"Processed this run: {processed_this_run} | Skipped: {skipped}"
                    )

    logging.info("========== CHUNK COMPLETE ==========")
    logging.info(f"PROCESSED THIS RUN: {processed_this_run}")
    logging.info(f"SKIPPED THIS RUN: {skipped}")
    logging.info("SCRIPT STOPPED – SAFE TO RUN AGAIN")


if __name__ == "__main__":
    main()
