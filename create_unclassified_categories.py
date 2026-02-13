"""
기존 사용자를 위한 "분류 전" 카테고리 생성 스크립트

이 스크립트는 이미 가입한 사용자들에게 "분류 전" 카테고리를 추가합니다.
새로운 사용자는 signals.py에서 자동으로 생성되므로 실행할 필요 없습니다.

사용 방법:
    python manage.py shell < create_unclassified_categories.py
    
또는:
    python manage.py shell
    >>> exec(open('create_unclassified_categories.py').read())
"""

from django.contrib.auth.models import User
from gallery.models import Category

def create_unclassified_for_existing_users():
    """기존 사용자들에게 "분류 전" 카테고리 생성"""
    
    users = User.objects.all()
    created_count = 0
    skipped_count = 0
    
    for user in users:
        # 이미 "분류 전" 카테고리가 있는지 확인
        existing = Category.objects.filter(
            user=user,
            name='분류 전'
        ).exists()
        
        if existing:
            print(f"⏭️  {user.username}: 이미 '분류 전' 카테고리가 있습니다.")
            skipped_count += 1
            continue
        
        # "분류 전" 카테고리 생성
        Category.objects.create(
            user=user,
            name='분류 전',
            category_key=None,
            parent=None
        )
        
        print(f"✅ {user.username}: '분류 전' 카테고리가 생성되었습니다.")
        created_count += 1
    
    print("\n" + "="*50)
    print(f"📊 결과:")
    print(f"   - 생성됨: {created_count}명")
    print(f"   - 건너뜀: {skipped_count}명")
    print(f"   - 전체: {users.count()}명")
    print("="*50)

if __name__ == "__main__":
    create_unclassified_for_existing_users()