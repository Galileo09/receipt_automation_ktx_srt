"""
영수증 자동화 대시보드 - FastAPI 백엔드

실행:
    cd web_ui
    uvicorn main:app --reload --port 8000
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from playwright.async_api import async_playwright

BASE_DIR      = Path(__file__).parent
REPO_DIR      = BASE_DIR.parent
KTX_DIR       = REPO_DIR / "receipt_automation_ktx"
SRT_DIR       = REPO_DIR / "receipt_automation_srt2"
SETTINGS_FILE = BASE_DIR / "settings.json"
GMAIL_PROFILE = BASE_DIR / "gmail_profile"
LOG_DIR       = REPO_DIR / "log"

LOG_DIR.mkdir(exist_ok=True)

app = FastAPI(title="영수증 자동화 대시보드")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


# ─── 설정 ─────────────────────────────────────────────────────────────────────

def load_settings() -> dict:
    # 기본 경로: 바탕화면/출장복명 (폴더 자동 생성)
    default_path = _resolve_save_path("Desktop/출장복명")
    defaults = {
        "recipient": "",
        "debug_mode": False,
        "ktx_save_path": default_path,
        "srt_save_path": default_path,
    }
    if SETTINGS_FILE.exists():
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        merged = {**defaults, **data}
        # 저장된 경로가 없거나 비어있으면 기본값 사용
        if not merged.get("ktx_save_path"):
            merged["ktx_save_path"] = default_path
        if not merged.get("srt_save_path"):
            merged["srt_save_path"] = default_path
        return merged
    return defaults


def save_settings(data: dict):
    SETTINGS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ─── Playwright 헬퍼 ──────────────────────────────────────────────────────────

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


# ─── Gmail 로그인 ─────────────────────────────────────────────────────────────

_gmail_logging_in = False


async def _do_gmail_login():
    global _gmail_logging_in
    _gmail_logging_in = True
    try:
        async with async_playwright() as p:
            ctx = await _get_playwright_context(p)
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            await page.goto("https://mail.google.com")
            await page.wait_for_url("**/mail.google.com/mail/**", timeout=600_000)
            await asyncio.sleep(1)
            await ctx.close()
    except Exception:
        pass
    finally:
        _gmail_logging_in = False


# ─── Gmail 발송 ───────────────────────────────────────────────────────────────

async def gmail_send(recipient: str, subject: str, body: str, files: list) -> str:
    if not GMAIL_PROFILE.exists() or not any(GMAIL_PROFILE.iterdir()):
        return "Gmail 로그인이 필요합니다."
    try:
        async with async_playwright() as p:
            ctx = await _get_playwright_context(p)
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()

            await page.goto("https://mail.google.com/mail/u/0/#inbox")
            await page.wait_for_load_state("domcontentloaded", timeout=30_000)

            # 쓰기 버튼이 보일 때까지 기다리는 것이 곧 Gmail SPA 초기화 완료 신호
            compose_btn = page.locator('[gh="cm"]')
            await compose_btn.wait_for(state="visible", timeout=30_000)
            await compose_btn.click()
            # 작성 창 애니메이션 대기
            await page.wait_for_timeout(1_000)

            compose = page.locator(
                'div[aria-label="New Message"], div[aria-label="새 메일"]'
            )
            await compose.wait_for(state="visible", timeout=15_000)

            # ── 받는사람 (Korean Gmail: aria-label="수신자") ──
            to_input = page.locator(
                'input[aria-label="수신자"], input[aria-label="To recipients"],'
                'input[aria-label="받는사람"]'
            )
            await to_input.wait_for(state="visible", timeout=10_000)
            await to_input.click()
            await to_input.fill(recipient)
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(300)

            # ── 제목 ──
            subject_input = page.locator('input[name="subjectbox"]')
            await subject_input.wait_for(state="visible", timeout=5_000)
            await subject_input.fill(subject)

            # ── 본문 (Korean Gmail: aria-label="메일 본문"; page 직접 접근) ──
            body_el = page.locator(
                'div[aria-label="메일 본문"], div[aria-label="Message Body"],'
                'div[aria-label="메시지 본문"]'
            )
            await body_el.wait_for(state="visible", timeout=5_000)
            await body_el.click()
            await page.keyboard.type(body)

            # ── 첨부파일 (버튼은 compose div 바깥에 위치) ──
            if files:
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

            # ── 보내기 ──
            send_btn = page.locator(
                '[data-tooltip*="보내기"], [data-tooltip*="Send"]'
            ).first
            await send_btn.wait_for(state="visible", timeout=5_000)
            await send_btn.click()
            await page.wait_for_timeout(3_000)
            await ctx.close()
            return ""
    except Exception as e:
        return f"Gmail 발송 오류: {e}"


# ─── 상태 관리 ────────────────────────────────────────────────────────────────

class AutomationState:
    def __init__(self):
        self.process: Optional[asyncio.subprocess.Process] = None
        self.status: str = "idle"
        self.log_file: Optional[Path] = None
        self.start_time: Optional[datetime] = None
        self.save_path: str = ""
        self.auto_send_email: bool = False
        self.new_files: list = []
        self.last_message: str = ""

    def write_log(self, line: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.last_message = line
        if self.log_file:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {line}\n")

    def is_running(self) -> bool:
        return self.process is not None and self.process.returncode is None

    def collect_new_files(self) -> list:
        if not self.save_path or not self.start_time:
            return []
        p = Path(self.save_path)
        if not p.exists():
            return []
        return sorted(
            str(f) for f in p.iterdir()
            if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) >= self.start_time
        )


ktx = AutomationState()
srt = AutomationState()


# ─── 비동기 stdout 읽기 ───────────────────────────────────────────────────────

async def _read_stdout(state: AutomationState):
    try:
        async for raw in state.process.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip("\n\r")
            if line:
                state.write_log(line)
    except Exception as e:
        state.write_log(f"[읽기 오류] {e}")

    rc = await state.process.wait()
    if rc != 0:
        state.status = "error"
        state.write_log(f"비정상 종료 (코드: {rc})")
        return

    state.write_log("자동화 완료")

    # 자동 메일 발송 (status는 아직 "running" — 완료 후 done으로 변경)
    if state.auto_send_email:
        state.new_files = state.collect_new_files()
        recv = load_settings().get("recipient", "")
        if recv and state.new_files:
            label   = "KTX" if state is ktx else "SRT"
            subject = f"[영수증] {label} {datetime.now().strftime('%Y-%m-%d')}"
            body    = f"{label} 영수증 자동화 완료\n\n첨부 파일 {len(state.new_files)}건"
            state.write_log(f"메일 발송 중 ({len(state.new_files)}건)...")
            err = await gmail_send(recv, subject, body, state.new_files)
            if err:
                state.write_log(f"메일 발송 실패: {err}")
            else:
                state.write_log(f"메일 발송 완료 → {recv}")
        elif not recv:
            state.write_log("수신자 이메일 미설정 — 메일 발송 건너뜀")
        else:
            state.write_log("생성된 파일 없음 — 메일 발송 건너뜀")

    state.status = "done"


def _resolve_save_path(save_path: str) -> str:
    """상대 경로 → 절대 경로 변환 및 폴더 생성. 오류 시 빈 문자열 반환."""
    try:
        p = Path(save_path).expanduser()
        if not p.is_absolute():
            p = Path.home() / p
        p.mkdir(parents=True, exist_ok=True)
        return str(p)
    except Exception:
        return ""


async def _start_process(state: AutomationState, cmd: list, cwd: Path,
                         save_path: str, auto_send: bool, label: str):
    if state.is_running():
        return False

    state.status = "running"
    state.start_time = datetime.now()
    state.save_path = save_path
    state.auto_send_email = auto_send
    state.new_files = []

    if load_settings().get("debug_mode", False):
        ts = state.start_time.strftime("%Y%m%d_%H%M%S")
        state.log_file = LOG_DIR / f"{label}_{ts}.log"
        state.write_log(f"=== {label.upper()} 자동화 시작 ===")
        state.write_log(f"기간: {cmd[cmd.index('--start_date')+1]} ~ {cmd[cmd.index('--end_date')+1]}")
        state.write_log(f"저장경로: {save_path}")
    else:
        state.log_file = None

    state.process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=cwd,
        env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"},
    )
    asyncio.create_task(_read_stdout(state))
    return True


# ─── 요청 모델 ────────────────────────────────────────────────────────────────

class StartRequest(BaseModel):
    start_date: str
    end_date: str
    save_path: str
    auto_send_email: bool = True


class EmailSettings(BaseModel):
    recipient: str
    debug_mode: bool = False
    ktx_save_path: str = ""
    srt_save_path: str = ""


class ManualSendRequest(BaseModel):
    key: str


# ─── 라우트 ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse((BASE_DIR / "static" / "index.html").read_text(encoding="utf-8"))


# ── Gmail 연동 ────────────────────────────────────────────────────────────────

@app.post("/api/gmail/login")
async def gmail_login():
    global _gmail_logging_in
    if _gmail_logging_in:
        return {"ok": False, "message": "이미 로그인 진행 중입니다."}
    asyncio.create_task(_do_gmail_login())
    return {"ok": True}


@app.get("/api/gmail/status")
async def gmail_status():
    connected = GMAIL_PROFILE.exists() and any(GMAIL_PROFILE.iterdir())
    return {"connected": connected, "logging_in": _gmail_logging_in}


# ── 설정 ─────────────────────────────────────────────────────────────────────

@app.get("/api/settings")
async def get_settings():
    s = load_settings()
    # 저장된 경로가 실제로 유효한지 확인 — 문제 있으면 빈 문자열로 반환
    for key in ("ktx_save_path", "srt_save_path"):
        path_val = s.get(key, "")
        if path_val:
            try:
                p = Path(path_val)
                if not p.exists():
                    p.mkdir(parents=True, exist_ok=True)
            except Exception:
                s[key] = ""
    return s


@app.post("/api/settings")
async def post_settings(req: EmailSettings):
    data = load_settings()
    data["recipient"]  = req.recipient
    data["debug_mode"] = req.debug_mode
    if req.ktx_save_path:
        data["ktx_save_path"] = _resolve_save_path(req.ktx_save_path)
    if req.srt_save_path:
        data["srt_save_path"] = _resolve_save_path(req.srt_save_path)
    save_settings(data)
    return {"ok": True, "ktx_save_path": data["ktx_save_path"], "srt_save_path": data["srt_save_path"]}


# ── 이메일 수동 발송 ──────────────────────────────────────────────────────────

@app.post("/api/email/send")
async def email_send(req: ManualSendRequest):
    state = ktx if req.key == "ktx" else srt
    if state.status != "done":
        return {"ok": False, "message": "자동화가 완료된 후에만 발송할 수 있습니다."}
    new_files = state.collect_new_files()
    if not new_files:
        return {"ok": False, "message": "이번 실행에서 생성된 파일이 없습니다."}
    recv = load_settings().get("recipient", "")
    if not recv:
        return {"ok": False, "message": "수신자 이메일을 먼저 저장해주세요."}

    label   = "KTX" if req.key == "ktx" else "SRT"
    subject = f"[영수증] {label} {datetime.now().strftime('%Y-%m-%d')}"
    body    = f"{label} 영수증 자동화 완료\n\n첨부 파일 {len(new_files)}건"
    err = await gmail_send(recv, subject, body, new_files)
    if err:
        state.write_log(f"수동 메일 발송 실패: {err}")
        return {"ok": False, "message": err}
    state.new_files = new_files
    state.write_log(f"수동 메일 발송 완료 → {recv} ({len(new_files)}건)")
    return {"ok": True, "count": len(new_files), "recipient": recv}


# ── KTX ──────────────────────────────────────────────────────────────────────

@app.post("/api/ktx/start")
async def ktx_start(req: StartRequest):
    if ktx.is_running():
        return {"ok": False, "message": "이미 실행 중입니다."}
    save_path = _resolve_save_path(req.save_path)
    cmd = [
        sys.executable, str(KTX_DIR / "korail_webview.py"),
        "--start_date", req.start_date,
        "--end_date",   req.end_date,
        "--save_path",  save_path,
    ]
    ok = await _start_process(ktx, cmd, KTX_DIR, save_path, req.auto_send_email, "ktx")
    return {"ok": ok, "log_file": str(ktx.log_file) if ktx.log_file else ""}


@app.post("/api/ktx/stop")
async def ktx_stop():
    if ktx.process and ktx.is_running():
        ktx.process.terminate()
        ktx.status = "idle"
        ktx.write_log("사용자가 중지했습니다.")
    return {"ok": True}


@app.get("/api/ktx/status")
async def ktx_status():
    return {"status": ktx.status, "log_file": str(ktx.log_file) if ktx.log_file else "", "last_message": ktx.last_message}


# ── SRT ──────────────────────────────────────────────────────────────────────

@app.post("/api/srt/start")
async def srt_start(req: StartRequest):
    if srt.is_running():
        return {"ok": False, "message": "이미 실행 중입니다."}
    save_path = _resolve_save_path(req.save_path)
    cmd = [
        sys.executable, str(SRT_DIR / "run.py"),
        "--start_date", req.start_date,
        "--end_date",   req.end_date,
        "--save_path",  save_path,
    ]
    ok = await _start_process(srt, cmd, SRT_DIR, save_path, req.auto_send_email, "srt")
    return {"ok": ok, "log_file": str(srt.log_file) if srt.log_file else ""}


@app.post("/api/srt/stop")
async def srt_stop():
    if srt.process and srt.is_running():
        srt.process.terminate()
        srt.status = "idle"
        srt.write_log("사용자가 중지했습니다.")
    return {"ok": True}


@app.get("/api/srt/status")
async def srt_status():
    return {"status": srt.status, "log_file": str(srt.log_file) if srt.log_file else "", "last_message": srt.last_message}
