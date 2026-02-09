import time
import os
import pyperclip
import re
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from config import Config
from xpath_config import XPathConfig

class SRTManager:
    def __init__(self, headless=Config.HEADLESS, log_callback=None):
        self.log_callback = log_callback
        self.options = Options()
        if headless:
            self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--start-maximized') # Fullscreen request
        # User agent to appear as a regular browser
        self.options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Persistent Profile
        self.options.add_argument(f"user-data-dir={Config.PROFILE_DIR}")
        
        # Suppress logging
        self.options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        self.driver = None

    def start_driver(self):
        if not self.driver:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)
            self.driver.implicitly_wait(Config.WAIT_TIMEOUT)

    def _log(self, msg):
        timestamp = time.strftime("[%H:%M:%S]")
        formatted_msg = f"{timestamp} {msg}"
        print(formatted_msg) # Console fallback
        if self.log_callback:
            self.log_callback(formatted_msg)

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def wait_for_login(self):
        self.start_driver()
        self._log(f"로그인 페이지로 이동 중: {Config.URL_LOGIN}")
        self.driver.get(Config.URL_LOGIN)
        
        self._log("사용자 로그인 대기 중... (브라우저에서 직접 로그인해주세요)")
        
        while True:
            try:
                # Check for "My Page" element to confirm login
                # XPath: /html/body/div[1]/header/div/div/div/div[2]/div/div/button
                # Also check if text contains '마이페이지' as requested (though XPath is strict, text check is safer)
                
                # First, ensure main page is loaded?
                # User asked to check if main page is open.
                # If we are redirected to main page, URL might change to https://etk.srail.kr/main.do
                
                my_page_btn = self.driver.find_elements(By.XPATH, XPathConfig.MY_PAGE_BTN)
                
                if my_page_btn:
                    btn_text = my_page_btn[0].text
                    if "마이페이지" in btn_text:
                        self._log("로그인 성공 확인 (마이페이지 감지됨).")
                        return True
                
                # Check if browser is closed
                try:
                    _ = self.driver.current_window_handle
                except:
                    self._log("브라우저가 닫혔습니다. 작업을 중단합니다.")
                    return False
                    
                time.sleep(1)
                
            except Exception as e:
                # If checking fails (e.g. alert open, switching pages), just continue waiting
                pass
            
            time.sleep(1)

    def goto_receipt_page(self):
        self._log(f"영수증 목록 페이지로 이동: {Config.URL_RECEIPT_LIST}")
        self.driver.get(Config.URL_RECEIPT_LIST)
        time.sleep(2)

    def capture_with_checkbox(self, limit=100, start_date=None, end_date=None, save_dir=None):
        # Set Dates if provided
        if start_date and end_date:
            try:
                self._log(f"기간 설정 시도: {start_date} ~ {end_date}")
                
                s_y = start_date[:4]
                s_m = start_date[4:6]
                s_d = start_date[6:8]
                e_y = end_date[:4]
                e_m = end_date[4:6]
                e_d = end_date[6:8]

                js_set_date = f"""
                function setVal(id, val) {{
                    var el = document.getElementById(id);
                    if (el) {{
                        el.value = val;
                        return true;
                    }}
                    return false;
                }}
                setVal('{XPathConfig.DATE_START_Y}', '{s_y}');
                setVal('{XPathConfig.DATE_START_M}', '{s_m}');
                setVal('{XPathConfig.DATE_START_D}', '{s_d}');
                setVal('{XPathConfig.DATE_END_Y}', '{e_y}');
                setVal('{XPathConfig.DATE_END_M}', '{e_m}');
                setVal('{XPathConfig.DATE_END_D}', '{e_d}');
                return 'OK';
                """
                self.driver.execute_script(js_set_date)
            except Exception as e:
                self._log(f"날짜 설정 중 오류 발생: {e}")

        # Search
        try:
            search_btn = self.driver.find_element(By.XPATH, XPathConfig.SEARCH_BTN)
            search_btn.click()
            time.sleep(2)
        except:
            self._log("조회 버튼 클릭 실패")

        if not save_dir:
            save_dir = Config.OUTPUT_DIR
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        page_num = 1
        previous_first_row_text = None
        
        while True:
            self._log(f"페이지 {page_num} 처리 중...")
            
            try:
                tbody = self.driver.find_element(By.XPATH, XPathConfig.RECEIPT_LIST_TABLE_BODY)
                rows = tbody.find_elements(By.TAG_NAME, "tr")
                
                if not rows:
                    self._log("데이터가 없습니다.")
                    break
                
                current_first_row_text = rows[0].text
                if current_first_row_text == previous_first_row_text:
                    self._log("마지막 페이지입니다.")
                    break
                previous_first_row_text = current_first_row_text
                
                # Inject JS to block print dialog in opened windows
                # This overrides window.open to hook into the new window and disable its print function
                js_block_print = """
                if (!window.oldOpen) {
                    window.oldOpen = window.open;
                    window.open = function(url, name, specs) {
                        var newWin = window.oldOpen(url, name, specs);
                        newWin.print = function() { console.log('Print blocked by automation'); };
                        return newWin;
                    };
                }
                """
                self.driver.execute_script(js_block_print)
                
                # Iterate rows by index to avoid staleness
                count = len(rows)
                for i in range(count):
                    try:
                        # Re-find row properly
                        tbody = self.driver.find_element(By.XPATH, XPathConfig.RECEIPT_LIST_TABLE_BODY)
                        row = tbody.find_elements(By.TAG_NAME, "tr")[i]
                        cols = row.find_elements(By.TAG_NAME, "td")
                        
                        if len(cols) < 11: continue

                        # 0:'', 1:Date, 2:Train, 3:Dep, 4:Arr, ... 8:Status, 9:Price
                        status = cols[8].text.strip()
                        
                        if "발권완료" in status:
                            # Extract Data
                            # Date: 1월 23일\n(금) -> 01월23일(금)
                            raw_date = cols[1].text.strip() # "1월 23일\n(금)"
                            # Train: SRT\n665
                            # Dep: 수서\n19:08
                            # Arr: 나주\n21:19
                            # Price: 41,300
                            
                            raw_dep = cols[3].text.strip() # "수서\n19:08"
                            raw_arr = cols[4].text.strip() # "나주\n21:19"
                            raw_price = cols[9].text.strip().replace(",", "") # "41,300" -> "41300"
                            
                            # Parse components
                            # Year is tricky. Assuming current year or passed year? 
                            # If passed start_date starts with 2024, assume 2024?
                            # Filename format: yy년mm월dd일(요일)(시분-시분)_출발지_목적지_가격
                            
                            # Date parsing
                            # raw_date looks like: "1월 23일\n(금)"
                            # Remove newlines
                            date_str = raw_date.replace("\n", "").replace(" ", "") # "1월23일(금)"
                            
                            # Add Year? User requested "yy년..."
                            # Let's derive year from start_date if available (e.g. 2026), or current.
                            # But SRT list might cross years.
                            # Assuming start_date year prefix.
                            year_prefix = start_date[2:4] if start_date else str(datetime.datetime.now().year)[2:]
                            
                            final_date_str = f"{year_prefix}년{date_str}" 
                            # date_str already has "mm월dd일(요일)" roughly? 
                            # Actually "1월23일(금)" -> we need "mm월dd일(요일)" format exactly.
                            # If raw is "1월 23일", we need to pad 0 if needed? "01월23일"?
                            # SRT shows "1월 23일".
                            
                            # Regex to robustly parse "X월 Y일(Z)"
                            import re
                            date_match = re.search(r"(\d+)월\s*(\d+)일\s*(\(.\))", raw_date.replace("\n", ""))
                            if date_match:
                                month = date_match.group(1).zfill(2)
                                day = date_match.group(2).zfill(2)
                                day_of_week = date_match.group(3) # (금)
                                
                                formatted_date = f"{year_prefix}년{month}월{day}일{day_of_week}"
                            else:
                                formatted_date = f"{year_prefix}년{raw_date.replace(' ', '')}"

                            # Time parsing
                            # "수서\n19:08"
                            dep_match = re.search(r"([^\d\n]+)\s*(\d{2}):(\d{2})", raw_dep.replace("\n", " "))
                            arr_match = re.search(r"([^\d\n]+)\s*(\d{2}):(\d{2})", raw_arr.replace("\n", " "))
                            
                            time_str = ""
                            dep_place = ""
                            arr_place = ""
                            
                            if dep_match:
                                dep_place = dep_match.group(1).strip()
                                dep_time = dep_match.group(2) + dep_match.group(3) # 1908
                            if arr_match:
                                arr_place = arr_match.group(1).strip()
                                arr_time = arr_match.group(2) + arr_match.group(3) # 2119
                                
                            time_part = f"({dep_time}-{arr_time})"
                            
                            filename = f"srt_{formatted_date}{time_part}_{dep_place}_{arr_place}_{raw_price}.png"
                            
                            # Clean invalid chars
                            filename = re.sub(r'[\\/*?:"<>|]', "", filename)
                            filepath = os.path.join(save_dir, filename)
                            
                            self._log(f"캡처 시도: {filename}")
                            
                            # 1. Check Checkbox
                            # XPath: //*[@id='list-form']/fieldset/div/table/tbody/tr[i+1]/td[1]/input
                            chk_xpath = XPathConfig.CHECKBOX_XPATH_TEMPLATE.format(i+1)
                            self.driver.find_element(By.XPATH, chk_xpath).click()
                            time.sleep(0.5)
                            
                            # 2. Click Print Button
                            self.driver.find_element(By.XPATH, XPathConfig.PRINT_BTN).click()
                            time.sleep(2)
                            
                            # 3. Switch to Popup
                            main_window = self.driver.current_window_handle
                            all_windows = self.driver.window_handles
                            if len(all_windows) > 1:
                                popup = [w for w in all_windows if w != main_window][-1]
                                self.driver.switch_to.window(popup)
                                
                                # Content should be captured without print dialog now
                                time.sleep(2) # Wait render
                                
                                # 4. Capture content
                                try:
                                    target = self.driver.find_element(By.XPATH, XPathConfig.POPUP_CONTENT)
                                    target.screenshot(filepath)
                                    self._log(f"저장 완료: {filepath}")
                                except Exception as e:
                                    self._log(f"스크린샷 저장 실패: {e}")
                                    
                                # 5. Close Popup
                                self.driver.close()
                                self.driver.switch_to.window(main_window)
                                time.sleep(1)
                            else:
                                self._log("인쇄 팝업이 뜨지 않았습니다.")
                                
                            # 6. Uncheck Checkbox (Robust Retry)
                            try:
                                for attempt in range(3):
                                    chk = self.driver.find_element(By.XPATH, chk_xpath)
                                    if chk.is_selected():
                                        self._log(f"체크박스 해제 시도 {attempt+1}...")
                                        # Use JS click for reliability
                                        self.driver.execute_script("arguments[0].click();", chk)
                                        time.sleep(0.5)
                                    else:
                                        self._log("체크박스 해제 확인됨.")
                                        break
                                
                                # Final check
                                chk = self.driver.find_element(By.XPATH, chk_xpath)
                                if chk.is_selected():
                                    self._log("경고: 체크박스가 여전히 선택되어 있습니다.")
                            except Exception as e:
                                self._log(f"체크박스 해제 중 오류: {e}")
                            
                    except Exception as e:
                        self._log(f"항목 {i+1} 처리 중 오류: {e}")
                        
            except Exception as e:
                if "invalid session id" in str(e).lower():
                    self._log("세션 종료됨.")
                    break
                self._log(f"오류: {e}")

            # Pagination
            try:
                next_btn_xpath = XPathConfig.NEXT_PAGE_BTN_INDEX
                next_btns = self.driver.find_elements(By.XPATH, next_btn_xpath)
                if next_btns:
                    next_btns[0].click()
                    time.sleep(2)
                    page_num += 1
                else:
                    self._log("마지막 페이지.")
                    break
            except:
                break
