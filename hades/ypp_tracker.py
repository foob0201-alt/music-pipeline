#!/usr/bin/env python3
"""
ypp_tracker.py — YPP 진입 지표 추적 (주 1회 실행 가정)

YouTube Data API channels.list(statistics)로 채널 지표를 조회하고,
YPP Tier 진입 진척도를 요약 + STATUS.md 에 append 한다.

한계(중요):
  - **90일 숏츠 조회수**는 YouTube **Analytics API**(별도 OAuth·리포트)가 필요하다.
    본 스크립트는 Analytics API 미연동 상태이므로, **채널 전체 누적 조회수(viewCount)**를
    숏츠뷰 프록시로 대체한다(상한선 근사, 실제 90일 숏츠뷰와 다름 — 연동 시 교체).
  - 공개영상 수(videoCount)는 공개/비공개 합계가 아닌 공개 기준(API 반환값).

출력: "구독 N/500 | 숏츠뷰(프록시) N/3,000,000 | 공개영상 N건"

사용:  python hades/ypp_tracker.py            # 조회 + STATUS.md append + 요약 출력
       python hades/ypp_tracker.py --json     # 원자료 JSON 도 출력
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS = ROOT / "STATUS.md"

SUB_GOAL = 500                 # Tier1 1단계 구독 목표
SHORTS_VIEW_GOAL = 3_000_000   # Tier1 대체경로: 90일 숏츠 300만뷰
CLIENT_SECRET = "client_secret.json"
TOKEN = "token.json"


def fetch_stats() -> dict:
    import sys
    sys.path.insert(0, str(ROOT))
    from upload_youtube import _service
    svc = _service(CLIENT_SECRET, TOKEN)
    resp = svc.channels().list(part="statistics,snippet", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        raise RuntimeError("channels.list 결과 없음 — 채널/토큰 확인")
    ch = items[0]
    st = ch.get("statistics", {})
    return {
        "channel_title": ch.get("snippet", {}).get("title"),
        "subscribers": int(st.get("subscriberCount", 0)),
        "total_views": int(st.get("viewCount", 0)),   # 숏츠뷰 프록시(누적 전체)
        "public_videos": int(st.get("videoCount", 0)),
    }


def fetch_regions(days: int = 90) -> dict:
    """Analytics API로 국가 상위 10 시청 데이터 조회(해외 유입 실측용).
    ⚠️ youtubeAnalytics 는 별도 스코프(yt-analytics.readonly)·API 사용설정 필요.
    현재 토큰은 youtube.force-ssl 만 → 미연동이면 한계 명시하고 빈 결과 반환."""
    try:
        import datetime as _dt
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds = Credentials.from_authorized_user_file(TOKEN)
        ya = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
        end = _dt.date.today()
        start = end - _dt.timedelta(days=days)
        r = ya.reports().query(
            ids="channel==MINE", startDate=start.isoformat(), endDate=end.isoformat(),
            metrics="views,estimatedMinutesWatched", dimensions="country",
            sort="-views", maxResults=10).execute()
        rows = r.get("rows", [])
        total = sum(row[1] for row in rows) or 1
        top = [{"country": row[0], "views": row[1], "minutes": row[2],
                "share": round(100 * row[1] / total, 1)} for row in rows]
        overseas = round(100 * sum(row[1] for row in rows if row[0] != "KR") / total, 1)
        return {"available": True, "days": days, "top10": top, "overseas_pct": overseas}
    except Exception as e:  # noqa: BLE001
        return {"available": False,
                "note": f"Analytics API 미연동 — yt-analytics.readonly 스코프 재인증 + "
                        f"API 사용설정 필요. ({type(e).__name__}: {str(e)[:80]})"}


def summary_line(s: dict) -> str:
    base = (f"구독 {s['subscribers']:,}/{SUB_GOAL} | "
            f"숏츠뷰(프록시) {s['total_views']:,}/{SHORTS_VIEW_GOAL:,} | "
            f"공개영상 {s['public_videos']}건")
    reg = s.get("regions", {})
    if reg.get("available"):
        top = reg["top10"][:3]
        base += " | 해외비율 %.1f%% (상위: %s)" % (
            reg["overseas_pct"], ", ".join(f"{r['country']} {r['share']}%" for r in top))
    else:
        base += " | 지역데이터: 미연동"
    return base


def append_status(s: dict, line: str) -> None:
    ts = s["_ts"]
    if not STATUS.exists():
        STATUS.write_text("# STATUS — YPP 지표 추적\n\n"
                          "> ypp_tracker.py 주 1회 append. 숏츠뷰=Analytics 미연동 → 누적 조회수 프록시.\n\n"
                          "| 일시 | 구독/500 | 숏츠뷰(프록시)/3M | 공개영상 |\n"
                          "|---|---|---|---|\n", encoding="utf-8")
    row = (f"| {ts} | {s['subscribers']:,}/{SUB_GOAL} | "
           f"{s['total_views']:,}/{SHORTS_VIEW_GOAL:,} | {s['public_videos']} |\n")
    with STATUS.open("a", encoding="utf-8") as f:
        f.write(row)


def main() -> int:
    ap = argparse.ArgumentParser(description="YPP 지표 추적")
    ap.add_argument("--json", action="store_true", help="원자료 JSON 출력")
    a = ap.parse_args()
    s = fetch_stats()
    s["regions"] = fetch_regions()
    s["_ts"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    line = summary_line(s)
    append_status(s, line)
    if a.json:
        print(json.dumps({k: v for k, v in s.items()}, ensure_ascii=False, indent=2))
    print(line)
    print(f"(STATUS.md append 완료: {STATUS})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
