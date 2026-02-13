# 🚄 KTX & SRT 영수증 자동화 (Korail & SRT Receipt Automation)

**"코딩은 모르지만, 불편함은 참을 수 없었습니다."**

이 프로젝트는 개발 지식이 전혀 없는 비개발자가 100% **AI와의 대화(Vibe Coding)**를 통해 완성한 **코레일 및 SRT 영수증 자동 다운로드 도구**입니다. 매달 증빙을 위해 하나하나 영수증을 클릭하고 저장해야 했던 번거로움을 해결하기 위해 만들었습니다.

---

## 🌟 제작 배경

* **주체:** 프로그래밍 언어를 한 줄도 모르는 비개발자
* **방법:** AI(Claude/Gemini)와 대화하며 코드를 짜고 오류를 수정하는 '바이브 코딩' 방식
* **목표:** 날짜만 입력하면 알아서 로그인하고, 영수증을 싹 긁어오는 자동화 도구 구현

---

## 🛠 주요 기능

* **자동 로그인:** 코레일(Korail) 및 SRT 계정 자동 접속
* **기간 조회:** 사용자가 지정한 기간 내의 승차권 이용 내역 검색
* **간편한 설정:** 복잡한 환경 설정 없이 실행할 수 있도록 최적화

---

## 🚀 시작하기

### 1. 사전 준비

이 프로그램을 실행하기 위해서는 Git과 Python이 설치되어 있어야 합니다.

Git 설치: https://git-scm.com/install/windows

Git 공식 다운로드 페이지에서 본인의 OS(Windows, macOS, Linux)에 맞는 버전을 설치해 주세요.

설치 완료 후 터미널(또는 CMD)에서 git --version을 입력하여 설치 여부를 확인할 수 있습니다.

Python 설치: https://www.python.org/downloads/ 

   ※ Python 3.8 이상의 버전이 필요합니다.


### 2. 설치 및 실행
Git 설치가 완료되었다면, 아래 명령어를 순서대로 입력하여 프로젝트를 복제하고 실행할 수 있습니다.
```bash
# 1. 레포지토리 복제
git clone https://github.com/Galileo09/receipt_automation_ktx_srt

# 2. 폴더 이동
cd receipt_automation_ktx
or
cd receipt_automation_srt

# 3. 필요한 라이브러리 설치
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4. 프로그램 실행
python launcher.py

# 5. SRT 미동작 시 대처 방법
cd receipt_automation_srt2

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python launcher.py

```

---

## 📖 사용 방법

1. 프로그램을 실행하면 나타나는 창에 **코레일/SRT 계정 정보**를 입력합니다.
2. 영수증을 추출할 **시작 날짜와 종료 날짜**를 선택합니다.
3. '실행' 버튼을 누르면 프로그램이 브라우저를 제어하여 자동으로 영수증을 저장합니다.
4. 저장된 영수증은 `../바탕화면/출장복명` 폴더에서 확인할 수 있습니다.

---

## 💡 꼭 읽어주세요! (제작자의 한마디)

> "개발자가 아니기에 코드 구조가 완벽하지 않을 수 있습니다. 하지만 **'나에게 필요한 것을 직접 만든다'**는 즐거움으로 한 땀 한 땀 AI와 대화하며 완성했습니다. 저와 비슷한 불편함을 겪는 분들이 계시다면 이 도구가 작게나마 도움이 되었으면 좋겠습니다. 잘 써주시면 정말 뿌듯할 것 같아요!"

---

## ⚖️ 면책 조항 (Disclaimer)

본 프로그램은 개인의 편의를 위해 제작된 자동화 도구입니다.

* 사용자의 계정 정보는 외부로 전송되지 않으며, 오직 로그인을 위해서만 사용됩니다.
* 과도한 요청으로 인한 사이트 이용 제한 등의 책임은 사용자 본인에게 있습니다.

---

## 🤝 기여 및 피드백

코드를 개선해 주실 능력자분들의 Pull Request나, 사용 중 발견된 버그 제보(Issues)는 언제나 환영합니다!

---
