import sys
from config import Config
from srt_manager import SRTManager

def main():
    print("=" * 50)
    print(" SRT Dynamic Receipt Automation (Selenium)")
    print("=" * 50)
    
    # 2. Initialize Manager
    manager = SRTManager()
    
    try:
        # 3. Wait for Manual Login
        if manager.wait_for_login():
            # 4. Navigate to Receipt Page
            manager.goto_receipt_page()
            
            # 5. Capture Receipts
            try:
                limit_str = input("Number of receipts to capture (Default 1): ").strip()
                limit = int(limit_str) if limit_str.isdigit() else 1
            except:
                limit = 1
                
            manager.capture_receipts(limit=limit)
            
        else:
            print("Login failed. Script stopping.")
            
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Ask to close or keep open? simpler to just close for automation
        print("Automation finished.")
        manager.close()

if __name__ == "__main__":
    main()
