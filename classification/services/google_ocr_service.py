from google.cloud import vision
import os
import io

class GoogleOCRService:
    """Google Cloud Vision API OCR 서비스"""
    
    def __init__(self):
        """초기화"""
        print("🔧 Google Cloud Vision API 초기화 중...")
        
        # JSON 파일 경로 (자동으로 찾음)
        # services/ 폴더에서 한 단계 위로 올라가서 google_credentials.json 찾기
        current_dir = os.path.dirname(__file__)  # services 폴더
        parent_dir = os.path.dirname(current_dir)  # classification 폴더
        credentials_path = os.path.join(parent_dir, "google_credentials.json")
        
        # JSON 파일 있는지 확인
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"❌ google_credentials.json 파일이 없습니다!\n"
                f"예상 경로: {credentials_path}\n"
                f"STEP 6을 다시 확인하세요."
            )
        
        # 환경 변수 설정
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        # Vision API 클라이언트 생성
        try:
            self.client = vision.ImageAnnotatorClient()
            print("✅ Google Cloud Vision API 준비 완료!\n")
        except Exception as e:
            raise Exception(f"❌ Vision API 초기화 실패: {e}")
    
    def extract_text(self, image_path):
        """
        이미지에서 텍스트 추출
        
        Args:
            image_path (str): 이미지 파일 경로
            
        Returns:
            dict: {
                'full_text': 전체 텍스트 (str),
                'lines': 라인별 텍스트 (list),
                'confidences': 신뢰도 (list)
            }
        """
        # 이미지 파일 확인
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"❌ 이미지를 찾을 수 없습니다: {image_path}")
        
        print(f"📸 이미지 분석 중: {os.path.basename(image_path)}")
        
        # 이미지 읽기
        with io.open(image_path, 'rb') as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)
        
        # OCR 실행 (손글씨 인식 강화 모드)
        response = self.client.document_text_detection(
            image=image,
            image_context={'language_hints': ['ko', 'en']}  # 한국어 우선
        )
        
        # 에러 체크
        if response.error.message:
            raise Exception(f"❌ Vision API 오류: {response.error.message}")
        
        # 결과가 없으면
        if not response.full_text_annotation:
            print("⚠️ 텍스트를 찾을 수 없습니다.")
            return {
                'full_text': '',
                'lines': [],
                'confidences': []
            }
        
        # 전체 텍스트
        full_text = response.full_text_annotation.text
        
        # 블록별 분석 (라인별 텍스트 + 신뢰도)
        lines = []
        confidences = []
        
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                block_text = ""
                
                # 블록 내 모든 단어 추출
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        word_text = ''.join([symbol.text for symbol in word.symbols])
                        block_text += word_text + " "
                
                # 블록에 텍스트가 있으면 추가
                if block_text.strip():
                    lines.append(block_text.strip())
                    confidences.append(block.confidence)
        
        print(f"✅ 텍스트 추출 완료 ({len(lines)}개 블록)")
        
        return {
            'full_text': full_text,
            'lines': lines,
            'confidences': confidences
        }


# ========================================
# 테스트 코드
# ========================================
if __name__ == "__main__":
    print("=" * 60)
    print("Google Cloud Vision API 테스트")
    print("=" * 60)
    print()
    
    try:
        # OCR 서비스 초기화
        ocr = GoogleOCRService()
        
        # 테스트 이미지 경로
        test_image = "../test_data/non_info/image.png"
        
        # 이미지 확인
        if not os.path.exists(test_image):
            print(f"⚠️ 테스트 이미지가 없습니다: {test_image}")
            print("test_data/ 폴더에 테스트 이미지를 넣어주세요.")
        else:
            # OCR 실행
            result = ocr.extract_text(test_image)
            
            # 결과 출력
            print()
            print("=" * 60)
            print("📄 추출된 전체 텍스트:")
            print("=" * 60)
            print(result['full_text'])
            
            print()
            print("=" * 60)
            print("📋 블록별 텍스트:")
            print("=" * 60)
            for i, (line, conf) in enumerate(zip(result['lines'], result['confidences']), 1):
                print(f"{i}. {line}")
                print(f"   신뢰도: {conf:.2%}")
            
            # 평균 신뢰도
            if result['confidences']:
                avg_conf = sum(result['confidences']) / len(result['confidences'])
                print()
                print("=" * 60)
                print(f"📊 평균 신뢰도: {avg_conf:.2%}")
                print("=" * 60)
    
    except FileNotFoundError as e:
        print(f"\n{e}")
        print("\n💡 해결 방법:")
        print("1. google_credentials.json 파일이 classification/ 폴더에 있는지 확인")
        print("2. STEP 5, 6을 다시 확인")
    
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        print("\n💡 가능한 원인:")
        print("1. Vision API가 활성화되지 않음 → STEP 3 확인")
        print("2. 서비스 계정 권한 부족 → STEP 4 확인")
        print("3. 인터넷 연결 문제")