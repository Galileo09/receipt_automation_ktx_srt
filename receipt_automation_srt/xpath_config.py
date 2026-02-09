class XPathConfig:
    # My Page (Login Success Indicator)
    MY_PAGE_BTN = "//button[@class='btn-navi my drop-btn']"
    
    # Search
    SEARCH_BTN = "//button[@class='btn_large btn_blue val_m']"
    # Date Inputs
    DATE_START_Y = "dptDtFromY"
    DATE_START_M = "dptDtFromM"
    DATE_START_D = "dptDtFromD"
    
    DATE_END_Y = "dptDtToY"
    DATE_END_M = "dptDtToM"
    DATE_END_D = "dptDtToD"

    # Receipt List
    RECEIPT_LIST_TABLE_BODY = "//*[@id='list-form']/fieldset/div/table/tbody"
    RECEIPT_BUTTONS = "//button[contains(text(), '영수증')]"
    RECEIPT_LINKS = "//a[contains(text(), '영수증')]"
    
    # Pagination
    PAGINATION_CONTAINER = "//*[@id='wrap']/div[4]/div/div[4]/div[4]"
    NEXT_PAGE_BTN = "//*[@id='wrap']/div[4]/div/div[4]/div[4]/a[contains(@class, 'next') or contains(text(), '다음')]"
    NEXT_PAGE_BTN_INDEX = "//*[@id='wrap']/div[4]/div/div[4]/div[4]/a[4]" 

    # New Checkbox Capture Flow
    # Checkbox in td[1]
    CHECKBOX_XPATH_TEMPLATE = "//*[@id='list-form']/fieldset/div/table/tbody/tr[{}]/td[1]/input" 
    # Print Button
    PRINT_BTN = "//button[@class='btn_large btn_emerald fs18 val_m']"
    # Popup Valid Content Area
    POPUP_CONTENT = "//*[@id='wrap']/div[2]/div[1]"
