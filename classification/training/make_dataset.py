import os
import pandas as pd
import sys

# -----------------------------------------------------------
# 1. 경로 설정 (services 폴더를 찾기 위해 상위 폴더 추가)
# -----------------------------------------------------------
# 현재 파일(make_dataset.py)의 부모의 부모 폴더(classification/)를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# -----------------------------------------------------------
# 2. 임포트 수정 (파일명과 클래스명을 실제 파일에 맞게 변경)
# -----------------------------------------------------------
from services.google_ocr_service import GoogleOCRService

def create_dataset_csv():
    # 설정
    data_dir = 'train_data'      # 이미지가 있는 폴더 (classification/train_data)
    output_file = 'train_text.csv' # 저장할 파일 이름
    
    # -------------------------------------------------------
    # 3. 클래스 생성 수정 (GoogleOCRService 사용)
    # -------------------------------------------------------
    try:
        ocr = GoogleOCRService() 
    except Exception as e:
        print(f"\n❌ OCR 서비스 초기화 실패: {e}")
        print("   google_credentials.json 파일 경로를 확인하세요.")
        return

    results = []
    
    print("=" * 60)
    print("📝 구글 OCR로 텍스트 추출 시작 (비용 발생 주의!)")
    print("=" * 60)

    # 폴더가 없으면 에러
    if not os.path.exists(data_dir):
        print(f"❌ '{data_dir}' 폴더가 없습니다. 프로젝트 최상위에서 실행했나요?")
        return

    # 폴더 탐색
    categories = sorted(os.listdir(data_dir))
    
    # 전체 파일 수 계산 (진행률 표시용)
    total_files = sum([len(files) for r, d, files in os.walk(data_dir)])
    processed_count = 0

    print(f"📂 총 {total_files}장의 이미지를 처리합니다...\n")

    for category in categories:
        folder_path = os.path.join(data_dir, category)
        if not os.path.isdir(folder_path): continue
        
        print(f"📂 [{category}] 폴더 처리 중...")
        
        files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
        
        if not files:
            print("   (이미지 없음)")
            continue

        for filename in files:
            img_path = os.path.join(folder_path, filename)
            
            try:
                # ---------------------------------------------------
                # 4. OCR 실행 (GoogleOCRService의 extract_text 호출)
                # ---------------------------------------------------
                response = ocr.extract_text(img_path)
                
                # 텍스트 추출 (딕셔너리에서 'full_text' 키 가져오기)
                if isinstance(response, dict):
                    text = response.get('full_text', '')
                else:
                    text = str(response)
                
                # 텍스트가 너무 짧으면(빈 텍스트 등) 무시할지 결정 (선택사항)
                # 여기서는 일단 다 저장합니다.
                
                results.append({
                    'filename': filename,
                    'category': category,
                    'text': text
                })
                
                processed_count += 1
                if processed_count % 5 == 0:
                    print(f"   👉 {processed_count}/{total_files}장 완료...")

            except Exception as e:
                print(f"   ⚠️ 에러 발생 ({filename}): {e}")

    # CSV 저장
    if results:
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print("\n" + "=" * 60)
        print(f"🎉 변환 완료! '{output_file}' 파일이 생성되었습니다.")
        print(f"   총 {len(results)}개의 데이터가 저장되었습니다.")
        print("=" * 60)
        print("미리보기:")
        print(df.head())
    else:
        print("\n❌ 저장할 데이터가 없습니다.")

if __name__ == "__main__":
    create_dataset_csv()