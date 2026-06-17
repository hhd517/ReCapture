<div align="center">

# Re:Capture

**무분별하게 쌓이는 사진을 사용자의 저장 목적에 따라 지능적으로 분류하고 관리해 주는 AI 기반 스마트 갤러리 서비스**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.x-092E20?style=flat-square&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat-square&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![GitHub](https://img.shields.io/badge/GitHub-pirogramming%2FReCapture-181717?style=flat-square&logo=github)](https://github.com/pirogramming/ReCapture)

> 피로그래밍 24기 최종 프로젝트 · 2026.01.25 ~ 02.19

</div>

---

## 📖 About

나중에 보려고 저장한 캡처와 사진, 정작 필요할 때 찾을 수가 없어서 답답했던 경험 있으신가요?

**Re:Capture**는 사용자가 사진을 올리는 순간, AI가 이미지와 텍스트를 함께 분석하여 **결제/예약 · 학습/노트 · 정보 · 기타** 4가지 카테고리로 자동 분류합니다. 더 이상 갤러리를 끝없이 스크롤하지 않아도 됩니다.

<br/>

## ✨ Features

| 기능 | 설명 |
|------|------|
| 🤖 **AI 자동 분류** | EfficientNet-B0(이미지) + KoELECTRA(텍스트) 앙상블 모델로 4개 카테고리 자동 분류 |
| 📱 **Google Photos 연동** | 모바일에서 캡처한 사진을 번거롭게 옮길 필요 없이 구글 포토로 실시간 동기화 |
| 📂 **드래그 & 드롭 업로드** | 로컬 파일 및 폴더 단위 업로드 지원, SHA-256 해시 기반 중복 사진 자동 제거 |
| 🔍 **스마트 검색 & 메모** | 이미지 내 텍스트 기반 검색 + 개별 사진 메모 기능 |
| 🔔 **리마인드 알림** | 설정한 시간 이상 확인하지 않은 카테고리의 사진을 자동 알림 |
| 🗑️ **자동 휴지통** | SHA-256 중복 제거 + 기간 지난 캡처본 자동 정리 |
| 📁 **커스텀 폴더** | 카테고리 외 사용자 정의 폴더 생성 및 관리 |

<br/>

## 🏗️ Architecture
Re:Capture/

├── accounts/          # 로그인 & 유저 관리, 구글 OAuth 연동

├── photos/            # 사진 수집 & 중복 제거, Google Photos API, 업로드 처리

├── classification/    # AI 분류 핵심 엔진

│   ├── services/

│   │   ├── image_classifier.py      # EfficientNet-B0 이미지 분류

│   │   ├── text_classifier.py       # KoELECTRA 텍스트 분류

│   │   ├── ensemble_classifier.py   # 앙상블 통합 분류기

│   │   ├── ocr_service.py           # OCR 텍스트 추출

│   │   └── google_ocr_service.py    # Google Vision OCR

│   └── training/                    # 모델 학습 스크립트

└── gallery/           # 북마크, 메모, 알림 등 서비스 기능 통합

<br/>

## 🤖 AI Classification Pipeline
사진 업로드

│

├─ [이미지 분석] EfficientNet-B0 → 1차 카테고리 예측

│

├─ [텍스트 추출] OCR (Google Vision / EasyOCR)

│       │

│       └─ [텍스트 분석] KoELECTRA → 2차 카테고리 예측

│

└─ [앙상블] 두 모델 결과 통합 + 키워드 규칙 후처리

│

└─ 결제/예약 · 학습/노트 · 정보 · 기타

카테고리별 약 300~350장 데이터로 학습, finance/info 카테고리 충돌 케이스는 키워드 규칙 기반 후처리로 보정합니다.

<br/>

## 👥 Contributors

| 이름 | 역할 | 담당 앱 |
|------|------|---------|
| 이서현 | PM · BE · AI | `classification` — AI 분류 핵심 엔진 |
| **한혜담** | **BE** | **`photos` — 사진 수집 & 중복 제거, Google Photos API, 업로드 전체 흐름** |
| 김나영 | BE · FE | `accounts` · `gallery` — 로그인/유저 관리, 기타 서비스 기능, 프론트엔드 |
| 박정해 | BE | `photos` — 업로드 로직 |
| 박선우 | BE · AI | `classification` — AI 분류 엔진 |

<br/>

## 🛠️ Tech Stack

**Backend**

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?style=flat-square&logo=django&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat-square&logo=mysql&logoColor=white)

**AI / ML**

![EfficientNet](https://img.shields.io/badge/EfficientNet--B0-FF6F00?style=flat-square)
![KoELECTRA](https://img.shields.io/badge/KoELECTRA--base--v3-5C6BC0?style=flat-square)
![OCR](https://img.shields.io/badge/OCR-EasyOCR%20%2F%20Google%20Vision-34A853?style=flat-square)

**Frontend**

![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)

**Infra / Tools**

![Google Photos API](https://img.shields.io/badge/Google%20Photos%20API-4285F4?style=flat-square&logo=google&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github)
![Notion](https://img.shields.io/badge/Notion-000000?style=flat-square&logo=notion)
![Figma](https://img.shields.io/badge/Figma-F24E1E?style=flat-square&logo=figma&logoColor=white)

<br/>

## 🚀 Getting Started

**1. 레포지토리 클론**

```bash
git clone https://github.com/pirogramming/ReCapture.git
cd ReCapture
```

**2. 가상환경 생성 및 패키지 설치**

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**3. 환경변수 설정**

`.env` 파일을 생성하고 아래 항목을 작성합니다.

```env
SECRET_KEY=your_secret_key
DATABASE_URL=mysql://user:password@localhost:3306/recapture
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

**4. DB 마이그레이션 및 서버 실행**

```bash
python manage.py migrate
python manage.py runserver
```

<br/>

## 🔄 develop 브랜치 최신화 체크리스트

`git pull` 후 아래 항목을 순서대로 확인하세요.

- [ ] `requirements.txt` 변경 → `pip install -r requirements.txt` 재실행
- [ ] `migrations/` 파일 변경 → `python manage.py migrate` 실행
- [ ] 코드(.py / .html / .css)만 변경 → 바로 `python manage.py runserver`

---

<div align="center">

피로그래밍 24기 · 2026

</div>
