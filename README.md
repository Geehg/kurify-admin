
# Kurify Admin v0.1

🎛️ 웹 기반 Kurify 등록 도구

## 기능
- 유튜브 링크 입력 → 오디오 다운로드 → fingerprint 생성 → DB 저장
- 제목과 아티스트는 수동 입력
- fingerprint만 저장, 음원은 자동 삭제

## 실행 방법
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

접속: http://127.0.0.1:8000
