# Re:Capture
나중에 보려고 저장한 캡처, 사진을 목적과 맥락 기준으로 정리해 주는 서비스

---
#### 🔄 develop 브랜치 최신화 이후 체크리스트
develop 브랜치를 `git pull`로 최신화한 뒤, 아래 항목 **반드시 확인**

#### 1️⃣ requirements.txt 변경 여부
`requirements.txt` 파일이 변경된 경우, 가상환경에서 **패키지 재설치가 필요**
```bash
pip install -r requirements.txt
```
⚠️ 설치 오류 또는 충돌 발생 시 → 가상환경 삭제 후 재생성을 권장

#### 2️⃣ migration 파일 변경 여부
app/migrations/000X_*.py 파일이 새로 추가되었거나 변경된 경우,
로컬 DB 반영을 위해 migration 실행이 필요
```bash
python manage.py migrate
```
#### 3️⃣ 위 두 항목이 모두 해당되지 않는 경우
코드(.py, .html, .css 등)만 변경된 경우 → 추가 작업 없이 바로 실행 가능
```bash
python manage.py runserver
```
