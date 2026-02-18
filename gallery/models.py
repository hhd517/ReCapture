from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class Category(models.Model):
    BASIC_CATEGORIES = [
        ('finance', '결제/예약'),
        ('study_note', '학습/노트'),
        ('info', '정보'),
        ('others', '기타'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=50)

    category_key = models.CharField(
        max_length=20,
        choices=BASIC_CATEGORIES,
        null=True, blank=True
    )

    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    is_bookmarked = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'name', 'parent')

    def __str__(self):
        return f"[{self.get_category_key_display()}] {self.name}" if self.category_key else self.name


class Photo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gallery_photos')

    # [파일 및 이미지 정보]
    image = models.ImageField(upload_to='photos/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    url = models.TextField(null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)

    # [해시 데이터]
    file_hash = models.CharField(max_length=64, db_index=True, null=True, blank=True)
    phash = models.CharField(max_length=16, db_index=True, null=True, blank=True)
    dhash = models.CharField(max_length=16, db_index=True, null=True, blank=True)
    ahash = models.CharField(max_length=16, null=True, blank=True)

    # [중복 관리]
    duplicate_of = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='duplicates',
        db_index=True,
    )

    # [분류 및 서비스 정보]
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='photos')
    memo = models.TextField(blank=True, null=True)
    is_bookmarked = models.BooleanField(default=False)
    is_confirmed = models.BooleanField(default=False)

    # [상태 정보 (휴지통 등)]
    is_trashed = models.BooleanField(default=False)
    trashed_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)  # Soft delete

    # ✅ 처리 상태(업로드 후처리 진행상황)
    PROCESSING_CHOICES = [
        ("PENDING", "대기"),
        ("PROCESSING", "처리중"),
        ("DONE", "완료"),
        ("FAILED", "실패"),
    ]
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_CHOICES,
        default="PENDING",
        db_index=True,
    )
    processing_error = models.TextField(null=True, blank=True)

    # [소스 정보]
    SOURCE_CHOICES = [('UPLOAD', 'Upload'), ('GOOGLE', 'Google')]
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='UPLOAD')
    google_id = models.CharField(max_length=255, null=True, blank=True, unique=True)

    # [메타데이터]
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    taken_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'combined_photos'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'file_hash'],
                condition=Q(file_hash__isnull=False, is_deleted=False),
                name='uniq_user_filehash_active',
            ),
        ]

    def __str__(self):
        return f"{self.filename} ({self.user.username})"

    @property
    def is_duplicate(self) -> bool:
        return self.duplicate_of_id is not None

    @property
    def expires_at(self):
        if self.trashed_at:
            return self.trashed_at + timedelta(days=30)
        return None

    def check_auto_trash(self, days=7):
        if not self.is_confirmed and self.created_at <= timezone.now() - timedelta(days=days):
            self.is_trashed = True
            self.trashed_at = timezone.now()
            self.save()
            return True
        return False


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, null=True, blank=True, related_name='reminders')
    message = models.CharField(max_length=255)
    notif_type = models.CharField(max_length=20, choices=[('reminder', '리마인드'), ('trash', '휴지통이동')])
    remind_at = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.user.username}] {self.message}"


class UserSetting(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    is_reminder_enabled = models.BooleanField(default=True)
    reminder_categories = models.ManyToManyField('Category', blank=True)
    reminder_days = models.IntegerField(default=7)

    is_auto_trash_enabled = models.BooleanField(default=False)
    auto_trash_categories = models.ManyToManyField('Category', related_name='trash_settings', blank=True)
    auto_trash_days = models.IntegerField(default=30)
    trash_expiry_days = models.IntegerField(default=30)

    def __str__(self):
        return f"{self.user.username}의 설정"