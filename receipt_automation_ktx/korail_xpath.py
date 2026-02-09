# Korail XPath Repository
# 이 파일은 코레일 자동화에 사용되는 XPath들을 정의합니다.

# Korail XPath Repository
# 이 파일은 코레일 자동화에 사용되는 XPath들을 정의합니다.

# 2. 메인 페이지 관련 XPath
# 상단 헤더의 로그아웃 링크
# 이 요소가 존재하면 로그인이 성공한 것으로 간주합니다.
MAIN_LOGOUT_LINK = "/html/body/div[1]/header/div/div[1]/div[2]/div[1]/div/ul[2]/li[2]/a"

# 3. 영수증(발권/취소 내역) 페이지 관련 XPath

# 조회하기 버튼
# /html/body/div[1]/div[3]/div/div/div/div/div[2]/div[2]/button
RECEIPT_INQUIRY_BTN = "/html/body/div[1]/div[3]/div/div/div/div/div[2]/div[2]/button"

# 1개월 조회 버튼
# /html/body/div[1]/div[3]/div/div/div/div/div[2]/div[1]/div/div/ul/li[3]
# 사용자가 제공한 경로 (li[3])를 그대로 사용, JS에서 클릭 대상 찾기
RECEIPT_1MONTH_BTN = "/html/body/div[1]/div[3]/div/div/div/div/div[2]/div[1]/div/div/ul/li[3]"

# 조회 결과 리스트 컨테이너
# /html/body/div[1]/div[3]/div/div/div/div/div[2]/div[3]/div[2]
RECEIPT_RESULT_LIST = "/html/body/div[1]/div[3]/div/div/div/div/div[2]/div[3]/div[2]"

# 더보기 버튼
# /html/body/div[1]/div[3]/div/div/div/div/div[2]/div[3]/a
RECEIPT_MORE_BTN = "/html/body/div[1]/div[3]/div/div/div/div/div[2]/div[3]/a"

# 선택 영수증 인쇄 버튼
# /html/body/div[1]/div[3]/div/div/div/div/div[2]/div[3]/div[1]/div[2]/button
RECEIPT_PRINT_BTN = "/html/body/div[1]/div[3]/div/div/div/div/div[2]/div[3]/div[1]/div[2]/button"

# 영수증 모달 영역 (캡처 대상)
# /html/body/div[5]/div/div/div/div[2]/div[1]/ul/li/div/div
RECEIPT_MODAL_AREA = "/html/body/div[5]/div/div/div/div[2]/div[1]/ul/li/div/div"

# 영수증 모달 닫기 버튼 (X 버튼)
# /html/body/div[5]/div/div/div/div[1]/button
RECEIPT_MODAL_CLOSE_BTN = "/html/body/div[5]/div/div/div/div[1]/button"
