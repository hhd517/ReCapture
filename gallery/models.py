from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime

class Photo(models.Model):
    # 1. 사용자 연결 (로그인 기능 관련)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='photos')
    
    # 사진 정보
    image = models.ImageField(upload_to='photos/%Y/%m/%d/')
    image_hash = models.CharField(max_length=64, unique=True) # 중복 감지용 SHA-256 해시
    source = models.CharField(max_length=20, choices=[('direct', 'Direct'), ('google', 'Google Drive')])
    
    # 3. 임시!!!! 사진 분류 (팀원 작업과 연동될 부분)
    category_main = models.CharField(max_length=50, default='기타') # 영수증, 수업자료 등
    category_sub = models.CharField(max_length=50, blank=True, null=True) # 미적분, 선형대수 등
    is_confirmed = models.BooleanField(default=False) # 사용자가 카테고리를 확인했는지 여부
    
    # 4. 기타 기능
    memo = models.TextField(blank=True, null=True) # 사진 한 줄 메모
    is_bookmarked = models.BooleanField(default=False) # 북마크 여부
    
    # 휴지통 기능
    is_trashed = models.BooleanField(default=False) # 휴지통 이동 여부
    trashed_at = models.DateTimeField(blank=True, null=True) # 휴지통에 버려진 시각
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.user.username}] {self.category_main} - {self.created_at}"

    # n일 이상 확인 안 하면 자동 휴지통 이동 여부 체크하는 메서드
    def check_auto_trash(self, days=7):
        if not self.is_confirmed and not self.is_trashed:
            if timezone.now() > self.created_at + datetime.timedelta(days=days):
                self.is_trashed = True
                self.trashed_at = timezone.now()
                self.save()

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    notif_type = models.CharField(max_length=20, choices=[('reminder', '리마인드'), ('trash', '휴지통이동')])
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.user.username}] {self.message}"