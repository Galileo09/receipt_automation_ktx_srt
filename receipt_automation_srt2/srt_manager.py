import asyncio
import json
import os
import re
import nodriver as uc
from config import Config
from log import log
from css import CSS
from jscode import JSCode


def _append_to_manifest(manifest_path: str, filepath: str):
    """manifest JSON에 저장된 파일 경로 추가"""
    if not manifest_path:
        return
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["files"].append(filepath)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"manifest 기록 실패: {e}")


class SRTManager:
    def __init__(self, manifest_path: str = ""):
        self.browser = None
        self.manifest_path = manifest_path

    async def start_browser(self):
        """브라우저 시작 - user_data_dir로 프로필 유지 (회원 아이디 저장 지원)"""
        if not self.browser:
            self.browser = await uc.start(
                user_data_dir=Config.PROFILE_DIR,
                headless=False
            )
        return self.browser

    async def close(self):
        """브라우저 종료"""
        if self.browser:
            try:
                self.browser.stop()
            except Exception:
                pass
            self.browser = None

    async def wait_for_login(self):
        """SRT 로그인 페이지로 이동하고 사용자가 로그인할 때까지 대기"""
        await self.start_browser()

        # 탭이 준비될 때까지 대기
        for _ in range(100):
            if self.browser.tabs:
                break
            await asyncio.sleep(0.1)

        if not self.browser.tabs:
            log("브라우저 탭을 찾을 수 없습니다.")
            return False

        tab = self.browser.tabs[0]
        log(f"로그인 페이지로 이동 중: {Config.URL_LOGIN}")
        await tab.get(Config.URL_LOGIN)

        log("사용자 로그인 대기 중... (브라우저에서 직접 로그인해주세요)")

        # 로그인 완료 대기 - URL 변경 감지
        while True:
            try:
                # 브라우저/탭 연결 상태 확인
                if not self.browser or not self.browser.tabs:
                    log("브라우저가 닫혔습니다.")
                    return False

                tab = self.browser.tabs[0]

                # URL 확인: main.do로 변경되면 로그인 성공
                current_url = tab.target.url if tab.target else ""
                if current_url and "main.do" in current_url:
                    log(f"로그인 성공 확인 (URL: {current_url})")
                    
                    # 영수증 페이지로 자동 이동
                    log(f"영수증 페이지로 이동 중: {Config.URL_RECEIPT_LIST}")
                    await tab.get(Config.URL_RECEIPT_LIST)
                    await asyncio.sleep(2)  # 페이지 로딩 대기
                    
                    log("영수증 페이지 이동 완료")
                    return True

            except BaseException as e:
                # CancelledError 등 모든 예외를 잡아서 루프 유지
                log(f"대기 중 예외 (무시): {type(e).__name__}")

            await asyncio.sleep(2)

    async def set_date_range(self, start_date, end_date):
        """
        영수증 페이지에 날짜 범위 설정
        
        Args:
            start_date: yyyyMMdd 형식의 시작일 (예: "20240201")
            end_date: yyyyMMdd 형식의 종료일 (예: "20240208")
        """
        if not self.browser or not self.browser.tabs:
            log("브라우저가 연결되지 않았습니다.")
            return False

        tab = self.browser.tabs[0]
        
        # 날짜 파싱
        start_year = start_date[:4]
        start_month = start_date[4:6]
        start_day = start_date[6:8]
        
        end_year = end_date[:4]
        end_month = end_date[4:6]
        end_day = end_date[6:8]
        
        log(f"날짜 설정: {start_year}-{start_month}-{start_day} ~ {end_year}-{end_month}-{end_day}")
        
        try:
            # select 요소 값 설정 (JavaScript 필요 - change 이벤트 발생 때문)
            await self._select_option_by_css(tab, CSS.DATE_START_YEAR, start_year)
            await asyncio.sleep(0.3)
            await self._select_option_by_css(tab, CSS.DATE_START_MONTH, start_month)
            await asyncio.sleep(0.3)
            await self._select_option_by_css(tab, CSS.DATE_START_DAY, start_day)
            await asyncio.sleep(0.3)
            
            await self._select_option_by_css(tab, CSS.DATE_END_YEAR, end_year)
            await asyncio.sleep(0.3)
            await self._select_option_by_css(tab, CSS.DATE_END_MONTH, end_month)
            await asyncio.sleep(0.3)
            await self._select_option_by_css(tab, CSS.DATE_END_DAY, end_day)
            
            log("날짜 설정 완료")
            return True
            
        except Exception as e:
            log(f"날짜 설정 중 오류 발생: {e}")
            return False

    async def _select_option_by_css(self, tab, selector, value):
        """select 요소의 option 선택 (JSCode 사용)"""
        js_code = JSCode.SELECT_VALUE_AND_TRIGGER_CHANGE.format(
            selector=selector,
            value=value
        )
        await tab.evaluate(js_code)

    async def click_search_button(self):
        """조회하기 버튼 클릭 - Python API 사용"""
        if not self.browser or not self.browser.tabs:
            log("브라우저가 연결되지 않았습니다.")
            return False

        tab = self.browser.tabs[0]
        
        try:
            log("조회하기 버튼 클릭 중...")
            
            # Python API로 요소 찾아서 클릭
            button = await tab.select(CSS.SEARCH_BUTTON)
            if button:
                await button.click()
                log("조회하기 버튼 클릭 완료")
                await asyncio.sleep(2)
                return True
            else:
                log("조회하기 버튼을 찾을 수 없습니다.")
                return False
                
        except Exception as e:
            log(f"조회하기 버튼 클릭 중 오류 발생: {e}")
            return False

    async def capture_receipts(self, save_dir):
        """발권완료된 영수증 캡처"""
        if not self.browser or not self.browser.tabs:
            log("브라우저가 연결되지 않았습니다.")
            return

        main_tab = self.browser.tabs[0]
        
        # 메인 탭에 인쇄 다이얼로그 차단 스크립트 주입
        await self._block_print_dialog(main_tab)
        
        try:
            # 전체 결과 행 개수 확인 - Python API
            rows = await main_tab.select_all(CSS.RESULT_ROWS)
            row_count = len(rows)
            log(f"총 {row_count}개의 결과 발견")
            
            captured_count = 0
            
            # 각 행 처리
            for row_num in range(1, row_count + 1):
                # 발권상태 확인 - JavaScript로 텍스트 추출
                status_selector = CSS.TICKET_STATUS_TEMPLATE.format(row=row_num)
                status_js = JSCode.GET_TEXT_CONTENT.format(selector=status_selector)
                try:
                    status = await main_tab.evaluate(status_js)
                except Exception as e:
                    log(f"행 {row_num}: 발권상태 추출 실패 - {e}")
                    status = None
                
                if status and "발권완료" in status:
                    log(f"행 {row_num}: 발권완료 - 처리 시작")
                    
                    # 체크박스 선택 - Python API
                    checkbox_selector = CSS.CHECKBOX_TEMPLATE.format(row=row_num)
                    try:
                        checkbox = await main_tab.select(checkbox_selector)
                        if checkbox:
                            await checkbox.click()
                            await asyncio.sleep(0.5)
                        else:
                            log(f"행 {row_num}: 체크박스를 찾을 수 없음")
                            continue
                    except Exception as e:
                        log(f"행 {row_num}: 체크박스 클릭 실패 - {e}")
                        continue
                    
                    # 영수증 인쇄 버튼 클릭하기 전에 인쇄 차단 스크립트 재주입
                    await self._block_print_dialog(main_tab)
                    
                    # 영수증 인쇄 버튼 클릭 - Python API
                    try:
                        print_button = await main_tab.select(CSS.PRINT_BUTTON)
                        if print_button:
                            await print_button.click()
                            await asyncio.sleep(2)  # 팝업 열릴 때까지 대기
                        else:
                            log(f"행 {row_num}: 인쇄 버튼을 찾을 수 없음")
                            continue
                    except Exception as e:
                        log(f"행 {row_num}: 인쇄 버튼 클릭 실패 - {e}")
                        continue
                    
                    # 팝업 탭 찾기
                    popup_tab = None
                    for tab in self.browser.tabs:
                        if tab != main_tab:
                            popup_tab = tab
                            break
                    
                    if popup_tab:
                        log(f"행 {row_num}: 팝업창 발견")
                        
                        # 팝업에도 즉시 인쇄 차단 주입
                        await self._block_print_dialog(popup_tab)
                        await asyncio.sleep(1)  # 팝업 완전히 로딩될 때까지 대기
                        
                        # 금액과 날짜 추출
                        filename = await self._extract_filename_from_popup(popup_tab)
                        
                        if filename:
                            # 스크린샷 저장
                            filepath = os.path.join(save_dir, f"{filename}.png")
                            await popup_tab.save_screenshot(filepath)
                            log(f"행 {row_num}: 저장 완료 - {filename}.png")
                            _append_to_manifest(self.manifest_path, filepath)
                            captured_count += 1
                        
                        # 팝업 닫기
                        await popup_tab.close()
                        await asyncio.sleep(0.5)
                    else:
                        log(f"행 {row_num}: 팝업창을 찾을 수 없음")
                    
                    # 체크박스 해제 - Python API
                    try:
                        checkbox = await main_tab.select(checkbox_selector)
                        if checkbox:
                            await checkbox.click()
                    except:
                        pass
                    
                else:
                    log(f"행 {row_num}: {status} - 건너뜀")
            
            log(f"영수증 캡처 완료: 총 {captured_count}건")
            
        except Exception as e:
            log(f"영수증 캡처 중 오류 발생: {e}")

    async def _block_print_dialog(self, tab):
        """인쇄 다이얼로그 차단 (JSCode 사용)"""
        try:
            await tab.evaluate(JSCode.BLOCK_PRINT_DIALOG)
        except Exception as e:
            log(f"인쇄 차단 스크립트 주입 실패: {e}")

    async def _extract_filename_from_popup(self, popup_tab):
        """팝업창에서 금액과 날짜 추출 - JavaScript 사용"""
        try:
            # 금액 추출 - JavaScript
            amount_js = JSCode.GET_TEXT_CONTENT.format(selector=CSS.POPUP_AMOUNT)
            amount_raw = await popup_tab.evaluate(amount_js)
            
            # 날짜 추출 - JavaScript
            date_js = JSCode.GET_TEXT_CONTENT.format(selector=CSS.POPUP_DATE)
            date_raw = await popup_tab.evaluate(date_js)
            
            if amount_raw and date_raw:
                # 금액 정리
                amount = re.sub(r'[\n\r\t]+', ' ', amount_raw)
                amount = re.sub(r'\s+', ' ', amount).strip()
                amount_cleaned = re.sub(r'[^0-9]', '', amount)
                
                # 여정 정보 정리
                journey_info = re.sub(r'[\n\r\t]+', ' ', date_raw)
                journey_info = re.sub(r'\s+', ' ', journey_info).strip()
                
                # → 를 " - "로 변경
                journey_cleaned = journey_info.replace("→", " - ")
                
                # 콜론 제거 (시간의 :)
                journey_cleaned = journey_cleaned.replace(":", "")
                
                # 파일명 생성: SRT_여정정보_금액
                # 예: SRT_2025-12-06 SRT 661 일반실 서울(1515) - 부산(1836)_66400
                #filename = f"SRT_{journey_cleaned}_{amount_cleaned}"
                filename = f"{journey_cleaned}_{amount_cleaned}"
                # Windows 금지 문자만 제거 (하이픈, 공백, 괄호는 유지)
                filename = re.sub(r'[<>"/\\|?*\x00-\x1f]', '', filename)
                
                log(f"생성된 파일명: {filename}")
                return filename
            else:
                log(f"데이터 추출 실패 - amount: {amount_raw}, date: {date_raw}")
            
        except Exception as e:
            log(f"파일명 추출 중 오류: {e}")
        
        return None
