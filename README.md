# NatNest Client

NAT 환경의 로컬 서버를 인터넷에 즉시 공개하는 SSH 리버스 터널 CLI입니다.  
`natnest 8080` 한 줄로 `https://<subdomain>.natnest.site` 주소를 얻을 수 있습니다.

---

## 빠른 설치

```bash
curl -fsSL https://natnest.site/install.sh | bash
```

> **지원 플랫폼:** Linux (amd64 · arm64), macOS, Windows 10/11  
> Windows는 아래 [수동 설치](#수동-설치)를 참고하세요.

설치 후 PATH에 추가된 디렉터리를 확인하세요 (출력 메시지에 안내됩니다).

---

## 시작하기

### 1단계 — Google 계정 연동

```bash
natnest setup
```

화면에 표시되는 URL을 브라우저에서 열고 코드를 입력하면 인증이 완료됩니다.

### 2단계 — 터널 열기

```bash
natnest 8080
```

성공하면 아래와 같이 공개 URL이 출력됩니다.

```
Tunnel active: https://yourname.natnest.site → localhost:8080
```

이제 어디서든 해당 URL로 로컬 서버에 접근할 수 있습니다.

---

## 명령어 참조

| 명령어 | 설명 |
|--------|------|
| `natnest setup` | Google 계정 연동 (최초 1회) |
| `natnest <port>` | 지정 포트로 터널 열기 |
| `natnest <port> <subdomain>` | 커스텀 서브도메인으로 터널 열기 |
| `natnest status` | 현재 활성 터널 목록 확인 |
| `natnest stop <port>` | 특정 포트의 터널 중지 |
| `natnest stop all` | 모든 터널 중지 |
| `natnest autostart` | 시스템 부팅 시 자동 시작 등록 |
| `natnest update` | 최신 버전으로 업데이트 |
| `natnest --version` | 클라이언트 버전 확인 |

### 커스텀 서브도메인 예시

```bash
natnest 3000 myapp
# → https://myapp.natnest.site
```

이미 사용 중인 서브도메인이면 대안을 자동으로 제안합니다.

---

## 수동 설치

설치 스크립트를 사용할 수 없는 환경에서는 바이너리를 직접 내려받으세요.

| 플랫폼 | 다운로드 |
|--------|---------|
| Linux (x86_64) | `https://natnest.site/natnest/linux/amd64/natnest` |
| Linux (ARM64 / Raspberry Pi) | `https://natnest.site/natnest/linux/arm64/natnest` |
| macOS | `https://natnest.site/natnest/macos/amd64/natnest` |
| Windows | `https://natnest.site/natnest/windows/amd64/natnest.exe` |

```bash
# Linux/macOS 예시
curl -Lo natnest https://natnest.site/natnest/linux/amd64/natnest
chmod +x natnest
sudo mv natnest /usr/local/bin/
```

---

## 동작 원리

```
[natnest CLI]
    │  SSH 리버스 터널 (port 2222)
    ▼
[NatNest 서버]  →  https://<subdomain>.natnest.site
```

- 클라이언트는 백그라운드 **watchdog 프로세스**를 띄워 SSH 연결을 유지합니다.
- 연결이 끊기면 5초 후 자동 재접속합니다.
- `natnest stop` 전까지 프로세스가 살아있으므로 터미널을 닫아도 터널은 유지됩니다.

---

## 개발 환경 설정

소스에서 직접 실행하거나 기여하려면 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)를 참고하세요.

```bash
git clone https://github.com/litdemon/natnest-client
cd natnest-client
pip install -r requirements.txt

# 목업 백엔드 실행
python docs/mock_backend.py

# 클라이언트 실행
NATNEST_SERVER_URL=http://localhost:8000 python main.py setup
NATNEST_SERVER_URL=http://localhost:8000 python main.py 8080
```

### 바이너리 빌드

```bash
# Linux / macOS
./build.sh          # → dist/natnest

# Windows
build.bat           # → dist\natnest.exe
```

---

## 문제 해결

**`natnest` 명령을 찾을 수 없다**  
설치 스크립트 출력에서 안내한 디렉터리가 `PATH`에 포함되어 있는지 확인하세요.

```bash
echo $PATH
```

**인증이 만료되었다**  
`natnest setup`을 다시 실행해 재인증하세요.

**터널이 갑자기 끊겼다**  
`~/.natnest/natnest.log`에서 watchdog 로그를 확인할 수 있습니다.

---

## 라이선스

MIT License — © NatNest
