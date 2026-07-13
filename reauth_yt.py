"""YouTube OAuth 재인증 — 브라우저 로그인(reina2hj)으로 새 token.json 발급.
실행(대화형):  .venv-align\\Scripts\\python.exe reauth_yt.py
브라우저가 자동으로 열림 → reina2hj 계정 로그인/동의 → token.json 자동 갱신.
v2 엔드포인트 강제(레거시 /o/oauth2/auth 404 회피). 로컬 서버가 code 자동 수신."""
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl",
          "https://www.googleapis.com/auth/yt-analytics.readonly"]
CLIENT_SECRET = "client_secret.json"
TOKEN = "token.json"

# 클라이언트 설정을 읽어 auth_uri 를 v2 로 교체
cfg = json.load(open(CLIENT_SECRET, encoding="utf-8"))
key = "installed" if "installed" in cfg else "web"
cfg[key]["auth_uri"] = "https://accounts.google.com/o/oauth2/v2/auth"

flow = InstalledAppFlow.from_client_config(cfg, SCOPES)
# 브라우저 열림 → 로컬 서버가 redirect(code) 자동 수신 → 교환
creds = flow.run_local_server(
    port=0, prompt="consent", access_type="offline",
    authorization_prompt_message="브라우저에서 reina2hj 계정으로 로그인/동의하세요...",
    success_message="재인증 완료. 이 탭을 닫고 채팅으로 돌아오세요.",
    open_browser=True,
)
with open(TOKEN, "w", encoding="utf-8") as f:
    f.write(creds.to_json())
print("REAUTH OK — token.json 갱신 완료. 이제 업로드 가능합니다.")
