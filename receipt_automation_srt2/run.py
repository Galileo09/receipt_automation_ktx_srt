"""
SRT 영수증 자동화 CLI 진입점
web_ui/main.py 에서 subprocess로 호출됨

사용 예시:
    python run.py --start_date 20250101 --end_date 20250131 --save_path "C:/receipts"
"""
import argparse
import asyncio
import sys
import os

# 현재 파일 위치를 sys.path에 추가 (srt_manager 등 import)
sys.path.insert(0, os.path.dirname(__file__))

from srt_manager import SRTManager
from log import log


async def run(start_date: str, end_date: str, save_path: str):
    manager = SRTManager()
    try:
        log(f"SRT 자동화 시작 | 기간: {start_date} ~ {end_date} | 저장경로: {save_path}")
        await manager.start_browser()
        await manager.wait_for_login()
        await manager.set_date_range(start_date, end_date)
        await manager.click_search_button()
        await manager.capture_receipts(save_path)
        log("SRT 자동화 완료")
    except Exception as e:
        log(f"[오류] {e}")
        sys.exit(1)
    finally:
        await manager.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SRT 영수증 자동화")
    parser.add_argument("--start_date", required=True, help="시작일 (yyyyMMdd)")
    parser.add_argument("--end_date", required=True, help="종료일 (yyyyMMdd)")
    parser.add_argument("--save_path", required=True, help="저장 폴더 경로")
    args = parser.parse_args()

    asyncio.run(run(args.start_date, args.end_date, args.save_path))
