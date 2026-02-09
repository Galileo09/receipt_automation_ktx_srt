import webview
import threading
import time
import os

# Define the target URLs
LOGIN_URL = "https://www.korail.com/ticket/login"
MAIN_PAGE_URL = "https://www.korail.com/ticket/main"
RECEIPT_PAGE_URL = "https://www.korail.com/ticket/mypage/ticketInfo/receipt"

import korail_xpath
import json

import datetime

def log_message(msg):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")

def monitor_logic(window, start_date, end_date, save_path):
    """
    Monitors the current URL and checks for login status on the main page.
    """
    log_message("Monitor logic started. Waiting for window initialization...")
    time.sleep(2)
    
    log_message(f"Target Range: {start_date} ~ {end_date}")

    # Using manual login now, so we just monitor for main page and receipt page.
    log_message("Waiting for manual login...")
    
    recepit_automation_done = False
    receipt_queue = [] # Queue of details to process
    current_processing_index = -1
    capture_started_index = -1 # Track if we triggered capture for current item
    
    # Pre-load html2canvas (will be injected when needed)
    HTML2CANVAS_URL = "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"
    html2canvas_script = None 
    
    try:
        import requests
        resp = requests.get(HTML2CANVAS_URL)
        if resp.status_code == 200:
            html2canvas_script = resp.text
            log_message("html2canvas script loaded in memory.")
        else:
            log_message("Failed to download html2canvas. Screenshot might fail.")
    except ImportError:
        log_message("Request module missing? Will try to inject via script tag if possible, or fail.")
        html2canvas_script = None

    while True:
        try:
            current_url = window.get_current_url()
            
            # --- Main Page Logic ---
            if current_url == MAIN_PAGE_URL:
                js_chk = f"""
                (function() {{
                    var result = document.evaluate('{korail_xpath.MAIN_LOGOUT_LINK}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                    return result.singleNodeValue ? result.singleNodeValue.innerText : null;
                }})()
                """
                text_content = window.evaluate_js(js_chk)
                
                if text_content and "로그아웃" in text_content:
                    log_message(f"로그인 성공 확인 ('{text_content}'). 영수증 페이지로 이동합니다...")
                    window.load_url(RECEIPT_PAGE_URL)
                    time.sleep(2) # 네비게이션 대기 (속도 개선)
            
            # --- Receipt Page Logic ---
            if current_url and current_url.startswith(RECEIPT_PAGE_URL) and not recepit_automation_done:
                # If we are processing the queue, don't re-run the search logic
                if len(receipt_queue) > 0 and current_processing_index < len(receipt_queue):
                    # We are in the loop, logic handled below
                    pass
                else: 
                     # Wait for load
                    ready_state = window.evaluate_js("document.readyState")
                    if ready_state != 'complete':
                        time.sleep(1)
                        continue
                    
                    # Logic: Click '1 Month' -> Inquiry -> Load All Pages -> Parse Results -> Filter '인쇄완료' -> Return Details
                    js_receipt = f"""
                    (function() {{
                        function getOne(xpath) {{
                            try {{
                                var res = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                                return res.singleNodeValue;
                            }} catch (e) {{
                                return null;
                            }}
                        }}

                        var btn1MonthNode = getOne("{korail_xpath.RECEIPT_1MONTH_BTN}");
                        var btnInquiry = getOne("{korail_xpath.RECEIPT_INQUIRY_BTN}");
                        
                        if (!btn1MonthNode || !btnInquiry) return 'MISSING_BUTTONS';
                        
                        // 1. Initial Search Click
                        if (!window.receiptSearchClicked) {{
                            // Click logic: try child button/a, else self
                            var clickable = btn1MonthNode.querySelector('button, a') || btn1MonthNode;
                            clickable.click();
                            
                            window.receiptSearchClicked = true;
                            // Use string for setTimeout to avoid scope issues in strict mode if any
                            setTimeout(function() {{ btnInquiry.click(); }}, 500);
                            return 'CLICKED_SEARCH';
                        }}
                        
                        // 2. Load All Pages (Click "More" until gone)
                        var moreBtn = getOne("{korail_xpath.RECEIPT_MORE_BTN}");
                        
                        if (moreBtn) {{
                            moreBtn.click();
                            return 'LOADING_MORE';
                        }}
                        
                        // 3. Extraction & Filtering
                        var listItems = document.querySelectorAll('.tckList');
                        
                        // Debug Container
                        var resultContainer = getOne("{korail_xpath.RECEIPT_RESULT_LIST}");
                        
                        if (listItems.length === 0) {{
                             if (resultContainer) {{
                                 return 'DEBUG_HTML|||' + resultContainer.outerHTML; 
                             }}
                             return 'WAITING_RESULTS';
                        }}
                        
                        var targetStart = parseInt('{start_date}');
                        var targetEnd = parseInt('{end_date}');
                        var matchedItems = [];
                        
                        for (var i=0; i<listItems.length; i++) {{
                            var item = listItems[i];
                            
                            // Filter: Must contain '인쇄완료'
                            if (!item.innerText.includes('인쇄완료')) {{
                                continue;
                            }}
                            
                            var dtSpan = item.querySelector('.dt');
                            if (!dtSpan) continue;
                            
                            var txt = dtSpan.innerText;
                            var parts = txt.match(/(\d{{4}})년\s*(\d{{2}})월\s*(\d{{2}})일/);
                            if (!parts) continue;
                            
                            var dateNum = parseInt(parts[1] + parts[2] + parts[3]);
                            
                            if (dateNum >= targetStart && dateNum <= targetEnd) {{
                                // Extract Details
                                var trainInfo = "";
                                var journeyInfo = "";
                                var source = "Unknown";
                                var destination = "Unknown";
                                var extractionTime = "Unknown";
                                var price = "Unknown";
                                
                                // Train Info (ex: KTX-산천 419)
                                var trainEl = item.querySelector('.tit_box .flag_wrap');
                                if (trainEl) trainInfo = trainEl.innerText.replace(/\\s+/g, ' ').trim();
                                
                                // Journey Info (ex: 서울 -> 부산(13:30 ~ 15:34))
                                var journeyEl = item.querySelector('.data_box h3');
                                if (journeyEl) {{
                                    journeyInfo = journeyEl.innerText.replace(/\\s+/g, ' ').trim();
                                    
                                    // Standardize arrow and parse
                                    var safeJourney = journeyInfo.replace('→', '->');
                                    var splitArrow = safeJourney.split('->');
                                    
                                    if (splitArrow.length >= 2) {{
                                        source = splitArrow[0].trim();
                                        
                                        var rightPart = splitArrow[1].trim();
                                        // rightPart ex: "부산 (12:30 ~ 15:34) 어른"
                                        
                                        var parenSplit = rightPart.split('(');
                                        if (parenSplit.length >= 2) {{
                                            destination = parenSplit[0].trim();
                                            
                                            // content inside parens: "13:30 ~ 15:34) 어른"
                                            var timeBlob = parenSplit[1];
                                            if (timeBlob.includes(')')) {{
                                                extractionTime = timeBlob.split(')')[0].trim();
                                            }} else {{
                                                extractionTime = timeBlob.trim();
                                            }}
                                        }} else {{
                                            destination = rightPart;
                                        }}
                                    }}
                                }}
                                
                                // Price extraction (find element containing '원' and no children)
                                var allEls = item.querySelectorAll('*');
                                for (var k=0; k<allEls.length; k++) {{
                                    if (allEls[k].children.length === 0 && allEls[k].innerText.includes('원')) {{
                                        price = allEls[k].innerText.trim();
                                        break;
                                    }}
                                }}
                                
                                matchedItems.push({{
                                    "date": parts[0],
                                    "source": source,
                                    "destination": destination,
                                    "time": extractionTime,
                                    "price": price,
                                    "train": trainInfo
                                }});
                            }}
                        }}
                        
                        if (matchedItems.length > 0) {{
                            return 'MATCHED_DETAILS|||' + JSON.stringify(matchedItems);
                        }}
                        
                        // If we found 'in-print' items but couldn't extract details, or found nothing matching date...
                        // Return container HTML to debug why parsing failed or logic skipped
                        if (resultContainer) {{
                             return 'DEBUG_HTML|||' + resultContainer.outerHTML; 
                        }}
                        
                        return 'NO_MATCHES';
                    }})()
                    """
                    
                    result = window.evaluate_js(js_receipt)
                    
                    if result == 'CLICKED_SEARCH':
                        log_message("'1개월' 버튼과 '조회' 버튼을 클릭했습니다. 결과를 기다리는 중...")
                        time.sleep(2)
                    elif result == 'LOADING_MORE':
                        log_message("'더보기' 버튼을 찾았습니다. 다음 페이지 로드 중...")
                        time.sleep(1.5)
                    elif result and result.startswith('DEBUG_HTML|||'):
                        html_content = result.split('DEBUG_HTML|||')[1]
                        log_message("!!! 디버그 HTML 캡처됨 !!!")
                        log_message("아래 내용을 복사해서 공유해주세요:")
                        log_message(html_content)
                        log_message("!!! 디버그 HTML 종료 !!!")
                        recepit_automation_done = True 
                    elif result == 'CLICKED_MORE':
                        log_message("현재 화면에 매칭 항목 없음. '더보기' 클릭. 추가 결과 대기 중...")
                        time.sleep(2)
                    elif result and result.startswith('MATCHED_DETAILS|||'):
                        json_str = result.split('MATCHED_DETAILS|||')[1]
                        try:
                            details = json.loads(json_str)
                            log_message(f"기간 내 영수증 {len(details)}개 선택됨 ({start_date}~{end_date}):")
                            log_message("----------------------------------------")
                            for item in details:
                                log_message(f" > 날짜: {item.get('date')}, 시간: {item.get('time')}")
                                log_message(f"   열차: {item.get('train')}")
                                log_message(f"   여정: {item.get('source')} -> {item.get('destination')}")
                                log_message(f"   가격: {item.get('price')}")
                                log_message("----------------------------------------")
                        except Exception as e:
                            log_message(f"항목을 선택했으나 상세 정보 파싱 실패: {e}")
                            
                        # Instead of finishing, start processing queue
                        if details:
                             receipt_queue = details
                             current_processing_index = 0
                             log_message(f"총 {len(receipt_queue)}개의 영수증 처리를 시작합니다. 하나씩 인쇄 및 저장합니다...")
                        else:
                             recepit_automation_done = True

                    elif result and result.startswith('NO_MATCHES'):
                        debug_info = ""
                        if '|||' in result:
                            debug_info = result.split('|||')[1]
                        log_message(f"검색 완료. 지정된 날짜 범위 내 영수증이 없습니다. 디버그(처음 5개 상태): {debug_info}")
                        recepit_automation_done = True
                    elif result == 'MISSING_BUTTONS':
                         log_message("조회 버튼이나 기간 설정 버튼을 찾을 수 없습니다.")
                    else:
                         pass
            
            # --- Processing Queue Loop ---
            if len(receipt_queue) > 0 and current_processing_index < len(receipt_queue):
                 item = receipt_queue[current_processing_index]
                 
                 # Step 1: Select Item and Open Print (Hijack window.open)
                 # We need to target the specific item by index in the list.
                 # The 'details' we got might not have index, so we assume order matches.
                 # Actually, let's just use the index `current_processing_index` and map it to DOM.
                 # BUT, we filtered by '인쇄완료'. We need to know which DOM index corresponds to this item.
                 # To simplify, we will re-scan DOM for '인쇄완료' and pick the N-th one.
                 
                 js_process = f"""
                 (function() {{
                     // Suppress print dialog
                     window.print = function() {{ console.log('Print dialog suppressed'); }};

                     var listItems = document.querySelectorAll('.tckList');
                     var targetIndex = -1;
                     var matchCount = 0;
                     
                     for (var i=0; i<listItems.length; i++) {{
                         if (listItems[i].innerText.includes('인쇄완료')) {{
                             if (matchCount === {current_processing_index}) {{
                                 targetIndex = i;
                                 break;
                             }}
                             matchCount++;
                         }}
                     }}
                     
                     if (targetIndex === -1) return 'ITEM_NOT_FOUND';
                     
                     // Uncheck all first
                     var allChecks = document.querySelectorAll('input[type="checkbox"]');
                     for (var i=0; i<allChecks.length; i++) allChecks[i].checked = false;
                     
                     // Check target
                     var targetItem = listItems[targetIndex];
                     var chk = targetItem.querySelector('input[type="checkbox"]');
                     if (chk) chk.click(); // Click to trigger events? or just checked=true
                     if (chk && !chk.checked) chk.checked = true;
                     
                     // Hijack window.open just in case, but keep in same window
                     window.open = function(url, name, specs) {{
                         // If it's a URL, we might want to follow it OR just let the modal appear if it's in-page.
                         // User report suggests 'modal appears'. If it's a real popup, window.open is used.
                         // We will redirect SELF to the URL if it's not empty.
                         if (url) window.location.href = url;
                         return window;
                     }};
                     
                     // Click Print Button
                     var printBtn = document.evaluate("{korail_xpath.RECEIPT_PRINT_BTN}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                     if (printBtn) {{
                         printBtn.click();
                         return 'CLICKED_PRINT';
                     }}
                     return 'PRINT_BTN_NOT_FOUND';
                 }})()
                 """
                 
                 # Only run this if we are on the LIST page (RECEIPT_PAGE_URL)
                 if current_url.startswith(RECEIPT_PAGE_URL):
                     res_proc = window.evaluate_js(js_process)
                     if res_proc == 'CLICKED_PRINT':
                         log_message(f"영수증 {current_processing_index+1}/{len(receipt_queue)} 선택 및 인쇄 클릭. 모달 대기...")
                         time.sleep(2) 
                     elif res_proc == 'ITEM_NOT_FOUND':
                         log_message("처리할 항목을 DOM에서 찾을 수 없습니다. (인덱스 불일치?)")
                         current_processing_index += 1 # Skip
                     else:
                         pass
                 
                 # Step 2: Check for Modal and Save
                 # We simply check if the Modal Area exists in the current DOM (whether redirected or not)
                 js_check_modal = f"""
                 (function() {{
                     var modalEntry = document.evaluate("{korail_xpath.RECEIPT_MODAL_AREA}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                     return modalEntry ? 'FOUND' : 'NOT_FOUND';
                 }})()
                 """
                 modal_status = window.evaluate_js(js_check_modal)
                 
                 if modal_status == 'FOUND':
                     # Ensure html2canvas is loaded
                     # Retry download if needed
                     if not html2canvas_script:
                         try:
                             import requests
                             resp = requests.get(HTML2CANVAS_URL)
                             if resp.status_code == 200:
                                 html2canvas_script = resp.text
                         except:
                             pass

                     # Injection Loop
                     for _ in range(5):
                         js_check_h2c = "typeof html2canvas !== 'undefined'"
                         is_loaded = window.evaluate_js(js_check_h2c)
                         if is_loaded:
                             break
                         
                         if html2canvas_script:
                             # Try evaluate
                             window.evaluate_js(html2canvas_script)
                         else:
                             # Try script tag injection
                             js_inject_cdn = f"""
                             var script = document.createElement('script');
                             script.src = "{HTML2CANVAS_URL}";
                             document.head.appendChild(script);
                             """
                             window.evaluate_js(js_inject_cdn)
                         
                         time.sleep(1)
                     
                     # Final Check
                     if not window.evaluate_js("typeof html2canvas !== 'undefined'"):
                         log_message("html2canvas 라이브러리 로드 실패. 캡처를 건너뜁니다.")
                         current_processing_index += 1
                         continue

                     # Construct Filename
                     
                     # Construct Filename
                     d = item.get('date', '0000년00월00일')
                     # Change yyyy -> yy
                     if len(d) >= 4 and d[:4].isdigit():
                         d = d[2:]
                     d = d.replace(" ", "")
                     
                     t = item.get('time', '00:00')
                     # Change HH:MM ~ HH:MM -> HHMM-HHMM
                     safe_time = t.replace(":", "").replace("~", "-").replace(" ", "")
                     
                     src = item.get('source', 'Unknown')
                     dst = item.get('destination', 'Unknown')
                     prc = item.get('price', '0').replace(",", "").replace("원", "")
                     
                     filename = f"ktx_{d}({safe_time})_{src}_{dst}_{prc}.png"
                     filename = "".join([c for c in filename if c.isalnum() or c in (' ', '.', '_', '(', ')', '-')]).strip()
                     full_save_path = os.path.join(save_path, filename)
                     
                     # Capture Logic with Polling
                     # 1. Trigger Capture if not started
                     if capture_started_index != current_processing_index:
                         log_message(f"이미지 생성 요청: {filename}")
                         
                         js_trigger = f"""
                         (function() {{
                             window._captureResult = null;
                             window._captureDone = false;
                             
                             var target = document.evaluate("{korail_xpath.RECEIPT_MODAL_AREA}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                             if (!target) {{
                                 window._captureResult = "ERROR:Target element not found";
                                 window._captureDone = true;
                                 return;
                             }}
                             
                             html2canvas(target).then(canvas => {{
                                 window._captureResult = canvas.toDataURL('image/png');
                                 window._captureDone = true;
                             }}).catch(err => {{
                                 window._captureResult = 'ERROR:' + err;
                                 window._captureDone = true;
                             }});
                         }})()
                         """
                         window.evaluate_js(js_trigger)
                         capture_started_index = current_processing_index
                     
                     # 2. Poll for Result
                     base64_data = window.evaluate_js("window._captureResult")
                     
                     if base64_data and base64_data.startswith('data:image/png;base64,'):
                         import base64
                         img_data = base64.b64decode(base64_data.split(',')[1])
                         
                         if os.path.exists(full_save_path):
                             log_message(f"이미 파일이 존재합니다. 덮어쓰기 수행: {full_save_path}")

                         with open(full_save_path, 'wb') as f:
                             f.write(img_data)
                         log_message(f"저장 완료: {full_save_path}")
                         
                         # Close Modal
                         log_message("모달 닫기 시도...")
                         js_close = f"""
                         (function() {{
                             var closeBtn = document.evaluate("{korail_xpath.RECEIPT_MODAL_CLOSE_BTN}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                             if (closeBtn) {{
                                 closeBtn.click();
                                 return 'CLICKED_CLOSE';
                             }}
                             // Fallback: history back if we navigated?
                             return 'NO_CLOSE_BTN';
                         }})()
                         """
                         res_close = window.evaluate_js(js_close)
                         
                         if res_close == 'NO_CLOSE_BTN':
                             # If we navigated away, maybe we need to go back
                             window.evaluate_js("window.history.back()")
                             
                         current_processing_index += 1
                         time.sleep(2) 
                     elif base64_data and str(base64_data).startswith('ERROR'):
                         log_message(f"캡처 실패: {base64_data}")
                         current_processing_index += 1
                     else:
                         log_message("캡처 데이터 대기 중... (처리 중)")
                         time.sleep(1)

            if len(receipt_queue) > 0 and current_processing_index >= len(receipt_queue):
                log_message("모든 영수증 처리가 완료되었습니다.")
                recepit_automation_done = True
                window.destroy()  # Auto-close window
                break
                
            time.sleep(1)
            
        except Exception as e:
            log_message(f"Error in monitoring loop: {e}")
            time.sleep(1)

import argparse

def main():
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_date", help="YYYYMMDD", default=today_str)
    parser.add_argument("--end_date", help="YYYYMMDD", default=today_str)
    parser.add_argument("--save_path", help="Path to save receipts", default=".")
    
    # Parse args once
    args = parser.parse_args()

    # Reverting to TEMP as requested.
    temp_dir = os.environ.get('TEMP') or os.path.expanduser("~")
    user_data_dir = os.path.join(temp_dir, 'korail_webview_data')
    
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
        
    log_message(f"Starting WebView with storage path: {user_data_dir}")
    log_message(f"Save Path set to: {args.save_path}")

    # Create window
    window = webview.create_window("Korail Receipt Automation", LOGIN_URL, width=1280, height=800)
    
    # Start thread
    t = threading.Thread(target=monitor_logic, args=(window, args.start_date, args.end_date, args.save_path))
    t.daemon = True
    t.start()
    
    # Ensure persistence by passing storage_path and disabling private_mode
    webview.start(private_mode=False, storage_path=user_data_dir)

if __name__ == '__main__':
    main()
