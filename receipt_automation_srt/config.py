import os

class Config:
    # URLs
    URL_LOGIN = "https://etk.srail.kr/cmc/01/selectLoginForm.do?pageId=TK0701000000"
    URL_RECEIPT_LIST = "https://etk.srail.kr/hpg/hta/03/selectBreakdownList.do?pageId=TK0102030100"
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR = os.path.join(BASE_DIR, "receipts")
    
    # Settings
    HEADLESS = False # Default to visible for reliability in this specific task, can be toggled
    WAIT_TIMEOUT = 10
    
    # Chrome Profile Path (System Temp)
    PROFILE_DIR = os.path.join(os.environ.get("TEMP"), "srt_chrome_profile")
    
    # Create output dir if not exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
