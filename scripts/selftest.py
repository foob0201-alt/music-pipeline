#!/usr/bin/env python3
"""
selftest.py — 음원/WhisperX 없이 자막 엔진을 검증한다.

KO 노랑채움 + 흰색 + EN 크림(색 분리)이 1440p 프레임에 실제로 구워지는지 픽셀로 확인.
사용: python scripts/selftest.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yaml  # noqa: E402
import align  # noqa: E402

KO = ["밤바다 위로 관람차가 돈다", "같은 풍경을 다시 데려오지만"]
EN = ["The ferris wheel turns over the night sea", "It brings back the same view again"]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    cfg = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
    cfg["subtitle"]["modes"] = ["dual"]

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        t = align.dummy_timings(KO, total=6.0)
        ass = td / "t.ass"
        ass.write_text(align.build_ass(cfg, "SELFTEST", "dual", t, EN), encoding="utf-8")

        cover = td / "c.jpg"
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                        "color=c=0x0a1428:s=2560x1440", "-frames:v", "1", str(cover)],
                       check=True, capture_output=True)
        frame = td / "f.png"
        esc = str(ass).replace(":", "\\:").replace("'", "\\'")
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(cover), "-t", "2",
                        "-vf", f"subtitles=filename='{esc}'", "-ss", "1.5",
                        "-frames:v", "1", str(frame)], check=True, capture_output=True)

        from PIL import Image
        px = Image.open(frame).convert("RGB").load()
        W, H = Image.open(frame).size
        y = w = c = 0
        for yy in range(0, H, 2):
            for xx in range(0, W, 2):
                r, g, b = px[xx, yy]
                if r > 180 and g > 140 and b < 120:
                    y += 1
                elif r > 200 and g > 200 and b > 200:
                    w += 1
                elif 150 < r < 235 and g > 195 and 175 < b < 235 and b > g - 40:
                    c += 1
        print(f"노랑(KO 채움)={y}  흰색(KO)={w}  크림(EN)={c}")
        ok = y > 50 and w > 50 and c > 50
        print("SELFTEST:", "PASS" if ok else "FAIL")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
