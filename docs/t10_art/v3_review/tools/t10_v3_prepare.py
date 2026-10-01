"""Create an immutable working snapshot and a provisional T10 v3 inventory."""

from __future__ import annotations

import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path

PROJECT = Path(r"C:\Sanguosha")
sys.path.insert(0, str(PROJECT / "src"))
from sanguosha.content.characters.standard import PLAYABLE_57_GENERAL_POOL  # noqa: E402


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"Invalid PNG: {path}")
    return struct.unpack(">II", header[16:24])


def main() -> None:
    art = PROJECT / "docs" / "t10_art"
    source = art / "v3_source_existing"
    review = art / "v3_review"
    candidates = art / "v3_candidates"
    manifest = json.loads((PROJECT / "assets" / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    counts = {}
    for character in PLAYABLE_57_GENERAL_POOL:
        cid = character.id
        pack = character.metadata["pack"]
        art_id = f"standard_{cid}" if pack == "standard" else cid
        path = PROJECT / "assets" / manifest[f"general.{cid}"]
        if not path.is_file():
            raise FileNotFoundError(path)
        group = "standard" if pack == "standard" else "myth_reborn_ordinary"
        dest = source / group / f"{art_id}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            if hashlib.sha256(dest.read_bytes()).digest() != hashlib.sha256(path.read_bytes()).digest():
                raise RuntimeError(f"Existing snapshot differs; refusing to overwrite: {dest}")
        else:
            shutil.copy2(path, dest)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        status = "keep" if cid == "wind_zhang_jiao" else "needs_upgrade"
        if status == "keep":
            keep = candidates / "wind_zhang_jiao.png"
            if keep.exists() and hashlib.sha256(keep.read_bytes()).hexdigest() != digest:
                raise RuntimeError(f"Protected Zhang Jiao candidate differs: {keep}")
            if not keep.exists():
                shutil.copy2(path, keep)
        counts[pack] = counts.get(pack, 0) + 1
        rows.append({
            "general_id": art_id,
            "runtime_general_id": cid,
            "中文名": character.name,
            "pack": pack,
            "faction": character.kingdom.value,
            "当前资源路径": str(path.relative_to(PROJECT)).replace("\\", "/"),
            "当前状态": status,
            "snapshot_path": str(dest.relative_to(PROJECT)).replace("\\", "/"),
            "sha256": digest,
            "dimensions": list(png_size(path)),
            "review_note": "原图已保护；待逐张视觉审查" if status != "keep" else "质量标杆；原样保留，禁止重绘",
        })
    if len(rows) != 57 or counts != {"standard": 25, "wind": 8, "fire": 8, "forest": 8, "mountain": 8}:
        raise RuntimeError(f"Unexpected roster: {len(rows)} / {counts}")
    review.mkdir(parents=True, exist_ok=True)
    (review / "portrait_inventory.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# T10 V3 现有头像审查清单",
        "",
        "当前状态为保守的初筛标记；除张角外，文件存在不代表已通过。逐张视觉审查后更新。",
        "",
        "| general_id | 中文名 | pack | faction | 当前资源路径 | 当前状态 | 尺寸 | 审查备注 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append("| " + " | ".join([
            row["general_id"], row["中文名"], row["pack"], row["faction"],
            row["当前资源路径"], row["当前状态"], "×".join(map(str, row["dimensions"])), row["review_note"]
        ]) + " |")
    (review / "portrait_inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"total": len(rows), "packs": counts, "snapshot_count": len(rows), "candidate_count": len(list(candidates.glob("*.png")))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
