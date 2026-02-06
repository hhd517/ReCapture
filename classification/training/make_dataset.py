import os
import pandas as pd
import sys

# OCR 텍스트 데이터셋 만들기 -> train_text.csv 생성

# -----------------------------------------------------------
# 1. 경로 설정
# -----------------------------------------------------------
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# -----------------------------------------------------------
# 2. 임포트
# -----------------------------------------------------------
from services.google_ocr_service import GoogleOCRService
from services.ocr_cache import OCRCache


def create_dataset_csv():
    data_dir = 'train_data'
    output_file = 'train_text.csv'

    # OCR 서비스 생성
    try:
        ocr = GoogleOCRService()
    except Exception as e:
        print(f"\n❌ OCR 서비스 초기화 실패: {e}")
        return

    cache = OCRCache(cache_dir="ocr_cache")

    results = []

    print("=" * 60)
    print("📝 구글 OCR로 텍스트 추출 시작")
    print("✅ 캐시 사용: 같은 이미지는 OCR 재호출 없음")
    print("=" * 60)

    if not os.path.exists(data_dir):
        print(f"❌ '{data_dir}' 폴더가 없습니다.")
        return

    categories = sorted(os.listdir(data_dir))

    exts = ('.jpg', '.jpeg', '.png')

    total_files = 0
    for r, d, files in os.walk(data_dir):
        total_files += sum(1 for f in files if f.lower().endswith(exts))

    processed_count = 0
    cache_hit = 0
    cache_miss = 0

    print(f"📂 총 {total_files}장의 이미지를 처리합니다...\n")

    for category in categories:
        folder_path = os.path.join(data_dir, category)
        if not os.path.isdir(folder_path):
            continue

        print(f"📂 [{category}] 폴더 처리 중...")

        files = [f for f in os.listdir(folder_path) if f.lower().endswith(exts)]

        for filename in files:
            img_path = os.path.join(folder_path, filename)

            try:
                cached = cache.load(img_path)

                # ⭐ HIT / MISS 로그 추가
                if cached is not None:
                    print(f"   ⚡ HIT  {category}/{filename}")
                    response = cached
                    cache_hit += 1
                else:
                    print(f"   🧠 MISS {category}/{filename} (OCR 호출)")
                    response = ocr.extract_text(img_path)
                    cache.save(img_path, response)
                    cache_miss += 1

                if isinstance(response, dict):
                    text = response.get('full_text', '')
                else:
                    text = str(response)

                results.append({
                    'filename': filename,
                    'category': category,
                    'text': text
                })

                processed_count += 1

                if processed_count % 5 == 0:
                    print(
                        f"   👉 {processed_count}/{total_files} 완료 "
                        f"(HIT={cache_hit}, MISS={cache_miss})"
                    )

            except Exception as e:
                print(f"   ⚠️ 에러 발생 ({filename}): {e}")

    # CSV 저장
    if results:
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')

        print("\n" + "=" * 60)
        print(f"🎉 변환 완료! '{output_file}' 생성")
        print(f"   총 데이터: {len(results)}")
        print(f"   ✅ 캐시 히트: {cache_hit}")
        print(f"   ✅ 캐시 미스: {cache_miss}")
        print(f"   📁 캐시 위치: {os.path.abspath('ocr_cache')}")
        print("=" * 60)

        print("미리보기:")
        print(df.head())
    else:
        print("\n❌ 저장할 데이터가 없습니다.")


if __name__ == "__main__":
    create_dataset_csv()
