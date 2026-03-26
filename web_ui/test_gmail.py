"""
Gmail 발송 단독 테스트
실행: cd web_ui && python test_gmail.py
"""
import asyncio
import json
import sys
import os
from pathlib import Path

BASE_DIR     = Path(__file__).parent
GMAIL_PROFILE = BASE_DIR / "gmail_profile"
SETTINGS_FILE = BASE_DIR / "settings.json"

sys.path.insert(0, str(BASE_DIR))

from playwright.async_api import async_playwright


async def _get_playwright_context(p):
    kwargs = dict(
        headless=False,
        args=[
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
        ],
        ignore_default_args=["--enable-automation"],
    )
    try:
        return await p.chromium.launch_persistent_context(
            str(GMAIL_PROFILE), channel="chrome", **kwargs
        )
    except Exception:
        return await p.chromium.launch_persistent_context(
            str(GMAIL_PROFILE), **kwargs
        )


async def gmail_send_test(recipient: str, subject: str, body: str, files: list) -> str:
    if not GMAIL_PROFILE.exists() or not any(GMAIL_PROFILE.iterdir()):
        return "Gmail 로그인이 필요합니다."
    try:
        async with async_playwright() as p:
            ctx = await _get_playwright_context(p)
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()

            print("[1] Gmail inbox로 이동...")
            await page.goto("https://mail.google.com/mail/u/0/#inbox")
            await page.wait_for_load_state("domcontentloaded", timeout=30_000)
            print(f"    현재 URL: {page.url}")

            print("[2] 쓰기 버튼 대기 (Gmail SPA 초기화 신호)...")
            compose_btn = page.locator('[gh="cm"]')
            await compose_btn.wait_for(state="visible", timeout=30_000)
            print("    쓰기 버튼 발견 — 클릭")
            await compose_btn.click()
            await page.wait_for_timeout(1_000)

            print("[3] 작성 창 대기...")
            compose = page.locator(
                'div[aria-label="New Message"], div[aria-label="새 메일"]'
            )
            await compose.wait_for(state="visible", timeout=15_000)
            print("    작성 창 열림")

            print("[4] 받는사람 입력...")
            to_input = page.locator(
                'input[aria-label="수신자"], input[aria-label="To recipients"],'
                'input[aria-label="받는사람"]'
            )
            await to_input.wait_for(state="visible", timeout=10_000)
            print(f"    받는사람 입력 — {recipient}")
            await to_input.click()
            await to_input.fill(recipient)
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(300)

            print("[5] 제목 입력...")
            subject_input = page.locator('input[name="subjectbox"]')
            await subject_input.wait_for(state="visible", timeout=5_000)
            await subject_input.fill(subject)

            print("[6] 본문 입력...")
            body_el = page.locator(
                'div[aria-label="메일 본문"], div[aria-label="Message Body"],'
                'div[aria-label="메시지 본문"]'
            )
            await body_el.wait_for(state="visible", timeout=5_000)
            await body_el.click()
            await page.keyboard.type(body)
            print("    본문 입력 완료")

            if files:
                print(f"[7] 첨부 파일 {len(files)}건...")
                attach_btn = page.locator(
                    '[data-tooltip="파일 첨부"], [data-tooltip="Attach files"],'
                    '[aria-label="파일 첨부"], [aria-label="Attach files"]'
                ).first
                await attach_btn.wait_for(state="visible", timeout=5_000)
                async with page.expect_file_chooser() as fc_info:
                    await attach_btn.click()
                fc = await fc_info.value
                await fc.set_files(files)
                await page.wait_for_timeout(2_000 * len(files))
                print("    첨부 완료")

            print("[8] 보내기 클릭...")
            send_btn = page.locator(
                '[data-tooltip*="보내기"], [data-tooltip*="Send"]'
            ).first
            await send_btn.wait_for(state="visible", timeout=5_000)
            await send_btn.click()
            await page.wait_for_timeout(3_000)
            await ctx.close()
            print("    발송 완료!")
            return ""
    except Exception as e:
        return f"Gmail 발송 오류: {e}"


async def main():
    settings = {}
    if SETTINGS_FILE.exists():
        settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))

    recipient = settings.get("recipient", "")
    if not recipient:
        print("ERROR: settings.json에 recipient 이메일이 없습니다.")
        sys.exit(1)

    # 바탕화면/출장복명에서 첨부 파일 수집
    save_path = settings.get("srt_save_path") or str(Path.home() / "Desktop" / "출장복명")
    save_dir = Path(save_path)
    files = sorted(str(f) for f in save_dir.iterdir() if f.is_file()) if save_dir.exists() else []
    print(f"수신자  : {recipient}")
    print(f"첨부파일: {len(files)}건 ({save_path})")

    err = await gmail_send_test(
        recipient=recipient,
        subject="[테스트] SRT 영수증 발송",
        body="Gmail 자동화 테스트 메일입니다.",
        files=files,
    )
    if err:
        print(f"\n실패: {err}")
        sys.exit(1)
    else:
        print("\n성공!")


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    asyncio.run(main())
