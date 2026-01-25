# 버밍엄 시티 FC 경기 일정 알림 프로그램

매일 아침 버밍엄 시티 FC의 경기 일정과 결과를 텔레그램으로 자동 전송하는 프로그램입니다.

## 주요 기능

- 오늘/내일 예정된 경기 일정
- 최근 경기 결과 (지난 24-48시간)
- 다음 주 전체 경기 일정 (향후 7일)
- 경기가 없는 날에도 알림 발송
- 매일 오전 9시 자동 실행 (cron 설정)

## 필수 요구사항

### 1. Python 환경
- Python 3.7 이상
- pip (Python 패키지 관리자)

### 2. API 키 및 토큰
다음 3가지를 사전에 준비해야 합니다:
1. football-data.org API 키
2. 텔레그램 봇 토큰
3. 텔레그램 Chat ID

## 설치 가이드

### 1단계: football-data.org API 키 발급

1. [football-data.org](https://www.football-data.org/client/register)에 접속
2. 계정 생성 (무료)
3. 로그인 후 대시보드에서 API 키 확인
4. 무료 플랜은 분당 10회 요청 가능 (이 프로그램에 충분함)

### 2단계: 텔레그램 봇 생성

1. 텔레그램에서 [@BotFather](https://t.me/botfather) 검색
2. `/newbot` 명령어 입력
3. 봇 이름 입력 (예: Birmingham City Notifier)
4. 봇 사용자명 입력 (예: birmingham_city_bot)
5. BotFather가 제공하는 **Bot Token** 저장

### 3단계: 텔레그램 Chat ID 확인

1. 텔레그램에서 [@userinfobot](https://t.me/userinfobot) 검색
2. 봇과 대화 시작
3. 봇이 알려주는 **Chat ID** 저장 (숫자)

### 4단계: 시놀로지 NAS에 프로젝트 설치

#### SSH 접속 활성화 (시놀로지 NAS)

1. 시놀로지 DSM에 로그인
2. **제어판** > **터미널 및 SNMP**
3. **SSH 서비스 활성화** 체크
4. 포트 확인 (기본: 22)

#### SSH로 NAS 접속

```bash
ssh your_username@your_nas_ip
```

#### Python 설치 확인

```bash
python3 --version
```

Python이 설치되어 있지 않다면:
1. DSM **패키지 센터**에서 "Python" 검색
2. Python 3 패키지 설치

#### 프로젝트 디렉토리 생성

```bash
# 스크립트 저장 디렉토리 생성
mkdir -p /volume1/scripts/birmingham-city-notifier
cd /volume1/scripts/birmingham-city-notifier
```

#### 파일 업로드

다음 방법 중 하나를 선택:

**방법 1: SCP로 파일 전송 (로컬 PC에서 실행)**
```bash
scp -r birmingham-city-notifier/* your_username@your_nas_ip:/volume1/scripts/birmingham-city-notifier/
```

**방법 2: Git 사용 (NAS에서 실행)**
```bash
cd /volume1/scripts
git clone <your-repository-url> birmingham-city-notifier
cd birmingham-city-notifier
```

**방법 3: 시놀로지 File Station**
1. File Station 열기
2. `scripts` 폴더로 이동
3. `birmingham-city-notifier` 폴더 생성
4. 모든 파일 업로드

### 5단계: 의존성 설치

```bash
cd /volume1/scripts/birmingham-city-notifier

# pip 설치 확인
python3 -m pip --version

# pip가 없다면 설치
wget https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py

# 의존성 패키지 설치
python3 -m pip install -r requirements.txt
```

### 6단계: 설정 파일 생성

```bash
cd /volume1/scripts/birmingham-city-notifier

# config.example.py를 복사하여 config.py 생성
cp config.example.py config.py

# nano 또는 vi로 config.py 편집
nano config.py
```

`config.py` 파일을 다음과 같이 수정:

```python
FOOTBALL_API_KEY = "abcd1234efgh5678"  # 1단계에서 받은 API 키
TELEGRAM_BOT_TOKEN = "123456:ABC-DEF1234"  # 2단계에서 받은 봇 토큰
TELEGRAM_CHAT_ID = "987654321"  # 3단계에서 받은 Chat ID
BIRMINGHAM_TEAM_ID = 332  # 변경하지 않음
```

저장: `Ctrl + O`, `Enter`, 종료: `Ctrl + X`

### 7단계: 테스트 실행

#### API 연동 테스트
```bash
python3 football_api.py
```

성공하면 버밍엄 시티의 경기 일정과 결과가 출력됩니다.

#### 텔레그램 전송 테스트
```bash
python3 telegram_bot.py
```

성공하면 텔레그램으로 테스트 메시지가 전송됩니다.

#### 전체 프로그램 테스트
```bash
python3 main.py
```

성공하면 텔레그램으로 실제 경기 정보가 전송됩니다.

### 8단계: 자동 실행 설정 (Cron)

#### 방법 1: 시놀로지 작업 스케줄러 (권장)

1. DSM에서 **제어판** > **작업 스케줄러**
2. **생성** > **예약된 작업** > **사용자 정의 스크립트**
3. 다음과 같이 설정:
   - **작업 이름**: Birmingham City Notifier
   - **사용자**: root 또는 본인 계정
   - **일정**: 매일, 09:00
   - **스크립트**:
     ```bash
     cd /volume1/scripts/birmingham-city-notifier && /usr/bin/python3 main.py >> /volume1/scripts/logs/birmingham-city.log 2>&1
     ```
4. **확인** 클릭

#### 방법 2: Crontab (SSH 사용)

```bash
# crontab 편집
crontab -e

# 다음 줄 추가 (매일 오전 9시 실행)
0 9 * * * cd /volume1/scripts/birmingham-city-notifier && /usr/bin/python3 main.py >> /volume1/scripts/logs/birmingham-city.log 2>&1

# 저장하고 종료
```

#### 로그 디렉토리 생성

```bash
mkdir -p /volume1/scripts/logs
```

#### Cron 작업 확인

```bash
# 현재 등록된 cron 작업 확인
crontab -l
```

### 9단계: 로그 확인

```bash
# 로그 파일 확인
tail -f /volume1/scripts/logs/birmingham-city.log
```

## 프로젝트 구조

```
birmingham-city-notifier/
├── main.py                 # 메인 실행 스크립트
├── football_api.py        # football-data.org API 클라이언트
├── telegram_bot.py        # 텔레그램 메시지 전송
├── config.py              # 설정 파일 (사용자가 생성)
├── config.example.py      # 설정 예시 파일
├── requirements.txt       # Python 의존성
├── README.md             # 이 파일
└── .gitignore            # Git 제외 파일
```

## 알림 메시지 예시

```
⚽ 버밍엄 시티 FC 경기 정보 (2026-01-26)

📅 오늘/내일 경기:
2026-01-26 15:00
Birmingham City vs Leeds United
장소: St Andrew's Stadium

📊 최근 경기 결과:
2026-01-23
Birmingham City 2 - 1 Sheffield Wednesday ✅

📆 다음 주 일정:
2026-01-29 19:45 - vs Norwich City (홈)
2026-02-01 15:00 - vs Millwall (원정)
```

## 문제 해결

### API 키 오류
- football-data.org API 키가 올바른지 확인
- API 요청 제한 초과 여부 확인 (무료: 10 req/min)

### 텔레그램 전송 실패
- 봇 토큰과 Chat ID가 올바른지 확인
- 봇과 대화를 시작했는지 확인 (봇에게 `/start` 전송)
- 네트워크 연결 확인

### Python 패키지 설치 오류
```bash
# pip 업그레이드
python3 -m pip install --upgrade pip

# 의존성 재설치
python3 -m pip install --force-reinstall -r requirements.txt
```

### Cron 작업이 실행되지 않음
```bash
# cron 서비스 상태 확인 (시놀로지)
synoservicectl --status crond

# cron 로그 확인
cat /var/log/cron.log

# 스크립트 실행 권한 확인
chmod +x /volume1/scripts/birmingham-city-notifier/main.py
```

### 버밍엄 시티 팀 ID 오류
- `BIRMINGHAM_TEAM_ID = 332`가 맞는지 확인
- football-data.org API에서 팀 ID 변경 여부 확인

## 추가 기능 (선택)

### 1. 로깅 개선
`main.py`에 더 자세한 로깅 추가 가능

### 2. 경기 전 알림
경기 시작 1시간 전 추가 알림을 받고 싶다면 별도 cron 작업 추가

### 3. 리그 순위 정보
Championship 순위표 정보 추가 가능

## 라이선스

MIT License

## 문의 및 기여

버그 리포트나 개선 제안은 이슈로 등록해주세요.

## 참고 링크

- [football-data.org API Documentation](https://www.football-data.org/documentation/quickstart)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Python Telegram Bot Library](https://python-telegram-bot.org/)
- [버밍엄 시티 FC 공식 사이트](https://www.bcfc.com/)
