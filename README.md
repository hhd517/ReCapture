<div align="center">

![header](https://capsule-render.vercel.app/api?type=blur&height=190&color=0:8FC2FF,50:4D8FD6,100:122F52&text=Re%3ACapture&fontSize=58&fontAlignY=50&fontColor=FFFFFF&animation=fadeIn)

**무분별하게 쌓이는 사진을 사용자의 저장 목적에 따라
지능적으로 분류하고 관리해 주는 AI 기반 스마트 갤러리 서비스**

<br/>

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square\&logo=python\&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.x-092E20?style=flat-square\&logo=django\&logoColor=white)](https://www.djangoproject.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat-square\&logo=mysql\&logoColor=white)](https://www.mysql.com/)
[![GitHub](https://img.shields.io/badge/GitHub-ReCapture-181717?style=flat-square\&logo=github\&logoColor=white)](https://github.com/pirogramming/ReCapture)

<br/>

**피로그래밍 24기 최종 프로젝트**
2026.01.25 ~ 2026.02.19

</div>

---

## 📖 About

나중에 보려고 저장한 캡처와 사진을 정작 필요할 때 찾지 못해 답답했던 경험이 있으신가요?

**Re:Capture**는 사용자가 사진을 추가하면 AI가 이미지와 내부 텍스트를 함께 분석해 **결제·예약, 학습·노트, 정보, 기타**의 4가지 카테고리로 자동 분류하는 스마트 갤러리 서비스입니다.

Google Photos 연동, 로컬 파일 업로드, 카메라 촬영 등 다양한 방식으로 사진을 추가할 수 있으며, 메모·검색·북마크·커스텀 폴더 기능을 통해 저장한 이미지를 다시 쉽게 찾고 관리할 수 있습니다.

더 이상 필요한 사진을 찾기 위해 갤러리를 끝없이 스크롤하지 않아도 됩니다.

<br/>

## ✨ Features

| 기능                      | 설명                                                               |
| ----------------------- | ---------------------------------------------------------------- |
| 🤖 **AI 자동 분류**         | EfficientNet-B0 이미지 모델과 KoELECTRA 텍스트 모델을 결합해 사진을 4개 카테고리로 자동 분류 |
| 📱 **Google Photos 연동** | Google Photos Picker를 통해 원하는 사진을 선택하고 Re:Capture로 가져오기           |
| 📷 **카메라 촬영**           | 모바일 환경에서 카메라로 사진을 촬영해 바로 서비스에 추가                                 |
| 📂 **드래그 앤 드롭 업로드**     | 로컬 파일 선택, 다중 이미지 및 드래그 앤 드롭 업로드 지원                               |
| ♻️ **중복 이미지 검사**        | SHA-256 해시값을 비교해 완전히 동일한 이미지의 중복 저장 방지                           |
| 🔍 **검색 및 메모**          | 사진별 메모 작성 및 메모 키워드를 이용한 이미지 검색                                   |
| ⭐ **북마크**               | 중요하거나 자주 확인하는 사진을 북마크로 관리                                        |
| 🗑️ **사진 삭제 관리**        | 여러 사진을 선택해 삭제하고 삭제 상태를 관리                                        |
| 📁 **커스텀 폴더**           | 기본 카테고리 외에 사용자 정의 폴더를 생성하고 사진을 이동·관리                             |

<br/>

## 🔄 Service Flow

```text
사진 추가
   ↓
이미지 저장
   ↓
SHA-256 기반 중복 검사
   ↓
이미지 및 텍스트 분석
   ↓
AI 자동 분류
   ↓
카테고리 및 사용자 폴더 저장
   ↓
메모·검색·북마크를 통한 관리
```

<br/>

## 🏗️ Architecture

```text
ReCapture/
├── accounts/                       # 로그인, 사용자 관리, Google OAuth 연동
├── photos/                         # 사진 수집, 업로드 및 중복 제거
│   ├── Google Photos Picker 연동
│   ├── Import Job API
│   ├── 사진 CRUD API
│   ├── SHA-256 기반 중복 검사
│   └── 이미지 업로드 처리
├── classification/                 # AI 분류 핵심 엔진
│   ├── services/
│   │   ├── image_classifier.py     # EfficientNet-B0 이미지 분류
│   │   ├── text_classifier.py      # KoELECTRA 텍스트 분류
│   │   ├── ensemble_classifier.py  # 이미지·텍스트 앙상블 분류
│   │   ├── ocr_service.py          # OCR 텍스트 추출
│   │   └── google_ocr_service.py   # Google Vision OCR
│   └── training/                   # 모델 학습 스크립트
└── gallery/                        # 갤러리 서비스 기능
    ├── 카테고리 및 사용자 폴더
    ├── 이미지 이동 및 삭제
    ├── 북마크
    └── 메모 및 검색
```

<br/>

## 🤖 AI Classification Pipeline

```text
사진 업로드
   │
   ├─ [이미지 분석]
   │  └─ EfficientNet-B0
   │     └─ 이미지 기반 1차 카테고리 예측
   │
   ├─ [텍스트 추출]
   │  └─ Google Vision OCR / EasyOCR
   │     └─ 이미지 내부 텍스트 추출
   │
   ├─ [텍스트 분석]
   │  └─ KoELECTRA
   │     └─ 텍스트 문맥 기반 2차 카테고리 예측
   │
   └─ [앙상블 분류]
      ├─ 이미지·텍스트 모델 결과 통합
      ├─ 키워드 규칙 기반 후처리
      └─ 결제·예약 / 학습·노트 / 정보 / 기타
```

카테고리별 약 300~350장의 데이터로 모델을 학습했습니다.

이미지의 시각적 특징은 **EfficientNet-B0**, 이미지 내부의 텍스트 문맥은 **KoELECTRA**를 통해 분석합니다. 두 모델의 예측 결과를 앙상블 방식으로 통합해 최종 카테고리를 결정합니다.

결제 화면과 상품 정보 화면처럼 시각적 구성이 유사해 `finance`와 `info` 카테고리 사이에서 충돌이 발생하는 경우에는 키워드 규칙 기반 후처리를 적용해 분류 결과를 보정했습니다.

<br/>

## 📂 Categories

| 카테고리      | 분류 예시                            |
| --------- | -------------------------------- |
| **결제·예약** | 영수증, 결제 내역, 예약 확인, 티켓, 교환권       |
| **학습·노트** | 수업 필기, 문제, 공식, 강의 자료, 공부 화면      |
| **정보**    | 상품 정보, 게시물, 주소, 링크, 안내 화면        |
| **기타**    | 인물, 풍경, 음식 등 다른 카테고리에 속하지 않는 이미지 |

AI가 분류한 결과가 사용자의 저장 목적과 다른 경우, 사진을 다른 카테고리나 사용자 폴더로 직접 이동할 수 있습니다.

<br/>

## 👥 Contributors

| 이름      | 역할           | 주요 담당                                                                              |
| ------- | ------------ | ---------------------------------------------------------------------------------- |
| **이서현** | PM · BE · AI | 프로젝트 기획, 이미지 분류 모델 학습 및 AI 분류 엔진 구현                                                |
| **한혜담** | BE           | Google Photos Picker·Import Job API, 사진 수집·중복 제거, `photos`·`gallery` 통합 및 인증 환경 개선 |
| **김나영** | BE · FE      | 로그인·사용자 관리, 갤러리 UI, 카테고리·폴더·북마크 기능 구현                                              |
| **박정해** | BE           | 사진 CRUD API, 이미지 업로드 로직 및 후처리 구조 구현                                                |
| **박선우** | BE · AI      | OCR, KoELECTRA 텍스트 분류, 앙상블 로직 및 메모 검색 구현                                           |

<br/>

## 🛠️ Tech Stack

### Backend

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square\&logo=python\&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.x-092E20?style=flat-square\&logo=django\&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat-square\&logo=mysql\&logoColor=white)

### AI / ML

![EfficientNet](https://img.shields.io/badge/EfficientNet--B0-FF6F00?style=flat-square)
![KoELECTRA](https://img.shields.io/badge/KoELECTRA--base--v3-5C6BC0?style=flat-square)
![OCR](https://img.shields.io/badge/OCR-EasyOCR%20%2F%20Google%20Vision-34A853?style=flat-square)

### Frontend

![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square\&logo=html5\&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square\&logo=css3\&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square\&logo=javascript\&logoColor=black)

### External API

![Google Photos API](https://img.shields.io/badge/Google%20Photos%20Picker-4285F4?style=flat-square\&logo=google\&logoColor=white)
![Google OAuth](https://img.shields.io/badge/Google%20OAuth-4285F4?style=flat-square\&logo=google\&logoColor=white)
![Google Vision](https://img.shields.io/badge/Google%20Vision%20OCR-4285F4?style=flat-square\&logo=googlecloud\&logoColor=white)

### Infra / Tools

![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat-square\&logo=github\&logoColor=white)
![Notion](https://img.shields.io/badge/Notion-000000?style=flat-square\&logo=notion\&logoColor=white)
![Figma](https://img.shields.io/badge/Figma-F24E1E?style=flat-square\&logo=figma\&logoColor=white)

<br/>

## 🚀 Getting Started

### 1. 레포지토리 클론

```bash
git clone -b develop https://github.com/pirogramming/ReCapture.git
cd ReCapture
```

### 2. 가상환경 생성 및 패키지 설치

#### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 아래 항목을 작성합니다.

```env
SECRET_KEY=your_secret_key
DATABASE_URL=mysql://user:password@localhost:3306/recapture

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

> 실제 환경변수 이름과 추가 설정은 프로젝트 설정 파일을 기준으로 확인해 주세요.

### 4. DB 마이그레이션

```bash
python manage.py migrate
```

### 5. 서버 실행

```bash
python manage.py runserver
```

<br/>

## 🔄 develop 브랜치 최신화 체크리스트

`develop` 브랜치를 최신 상태로 업데이트합니다.

```bash
git switch develop
git pull origin develop
```

업데이트 후 아래 항목을 확인합니다.

* [ ] `requirements.txt`가 변경된 경우

```bash
pip install -r requirements.txt
```

* [ ] `migrations/` 파일이 추가되거나 변경된 경우

```bash
python manage.py migrate
```

* [ ] Python, HTML, CSS, JavaScript 코드만 변경된 경우

```bash
python manage.py runserver
```

---

<div align="center">

**저장한 순간의 목적을 다시 찾다.**

### Re:Capture

피로그래밍 24기 · 2026

</div>
