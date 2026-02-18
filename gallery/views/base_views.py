# gallery/views/base_views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from gallery.models import Photo, UserSetting, Category
from django.db.models import Q, Case, When, IntegerField, Value


def build_move_category_options(user):
    # 대분류 (원하는 순서로 고정)
    roots = (
        Category.objects
        .filter(user=user, parent=None)
        .exclude(name="분류 전")   # 이동 대상에서 분류 전 제외(기존 로직 유지)
        .annotate(
            sort_order=Case(
                When(name="결제/예약", then=Value(1)),
                When(name="학습/노트", then=Value(2)),
                When(name="정보", then=Value(3)),
                When(name="기타", then=Value(4)),
                default=Value(999),
                output_field=IntegerField(),
            )
        )
        .order_by("sort_order", "id")
    )

    # 소분류 (내가 만든 폴더)
    subs = Category.objects.filter(user=user).exclude(parent=None).order_by(
        "parent_id", "name"
    )

    sub_map = {}
    for s in subs:
        sub_map.setdefault(s.parent_id, []).append(s)

    options = []
    for r in roots:
        options.append({"id": r.id, "label": r.name})
        for s in sub_map.get(r.id, []):
            options.append({"id": s.id, "label": f"└ {s.name}"})

    return options


@login_required
@login_required
def settings_view(request):
    # 설정 객체가 없으면 생성
    setting, created = UserSetting.objects.get_or_create(user=request.user)
    categories = Category.objects.filter(user=request.user)

    # 구글 포토 연동 상태 확인
    from photos.models import GoogleCredential
    google_connected = False
    google_email = None
    try:
        google_cred = GoogleCredential.objects.get(user=request.user)
        google_connected = True
        google_email = google_cred.google_email
    except GoogleCredential.DoesNotExist:
        pass

    if request.method == 'POST':
        # 알림 설정 업데이트
        setting.is_reminder_enabled = request.POST.get('is_reminder') == 'on'
        setting.reminder_days = int(request.POST.get('reminder_days', 7))
        setting.reminder_categories.set(request.POST.getlist('reminder_cats'))

        # 휴지통 설정 업데이트
        setting.is_auto_trash_enabled = request.POST.get('is_auto_trash') == 'on'
        setting.auto_trash_days = int(request.POST.get('auto_trash_days', 30))
        setting.trash_expiry_days = int(request.POST.get('trash_expiry', 30))
        # setting.auto_trash_categories.set(request.POST.getlist('trash_cats'))

        setting.save()
        return redirect('gallery:settings')

    return render(request, 'gallery/settings.html', {
        'setting': setting,
        'categories': categories,
        'google_connected': google_connected,
        'google_email': google_email,
    })


@login_required(login_url='/accounts/login/')
def photo_list(request):
    photos = Photo.objects.filter(user=request.user, is_trashed=False)

    # 대분류 카테고리만 가져오기 (parent가 없는 것들) + 원하는 순서로 고정
    categories = (
        Category.objects
        .filter(user=request.user, parent=None)
        .annotate(
            sort_order=Case(
                When(name="결제/예약", then=Value(1)),
                When(name="학습/노트", then=Value(2)),
                When(name="정보", then=Value(3)),
                When(name="기타", then=Value(4)),
                When(name="분류 전", then=Value(5)),
                default=Value(999),
                output_field=IntegerField(),
            )
        )
        .order_by("sort_order", "id")
    )

    category_id = request.GET.get('category_id')
    sub_category_id = request.GET.get('sub_category_id')
    is_bookmarked = request.GET.get('bookmarked')
    query = request.GET.get('q')

    sub_categories = []
    current_category_name = None

    # [검색 기능 추가] 검색어가 있으면 메모(memo) 또는 파일명(filename)에서 검색
    if query:
        photos = photos.filter(
            Q(memo__icontains=query) |
            Q(filename__icontains=query)
        )

    # 1. 카테고리 필터 적용 로직 개선
    if category_id:
        # 현재 대분류 정보 및 소분류 리스트 가져오기
        sub_categories = Category.objects.filter(user=request.user, parent_id=category_id)

        try:
            current_cat = Category.objects.get(id=category_id)
            current_category_name = current_cat.name
        except Category.DoesNotExist:
            pass

        if sub_category_id:
            # [Case 1] 소분류가 선택된 경우: 해당 소분류 사진만 필터링
            photos = photos.filter(category_id=sub_category_id)
        else:
            # [Case 2] 대분류만 선택된 경우: 대분류 본인 + 하위 소분류 사진 모두 포함
            sub_cat_ids = sub_categories.values_list('id', flat=True)
            photos = photos.filter(Q(category_id=category_id) | Q(category_id__in=sub_cat_ids))
            # 💡 기존의 photos.filter(category_id=category_id)를 위 코드로 대체했습니다.

    # 2. 북마크 필터 적용
    if is_bookmarked == 'true':
        photos = photos.filter(is_bookmarked=True)

    return render(request, 'gallery/photo_list.html', {
        'photos': photos.order_by('-created_at'),
        'categories': categories,
        'sub_categories': sub_categories,
        'move_category_options': build_move_category_options(request.user),
        'current_category': int(category_id) if category_id else None,
        'current_sub_category': int(sub_category_id) if sub_category_id else None,
        'current_category_name': current_category_name,
        'is_bookmarked': is_bookmarked == 'true',
        'query': query,
    })


@login_required(login_url='/accounts/login/')
def photo_detail(request, photoid):
    photo = get_object_or_404(Photo, id=photoid, user=request.user)
    return render(request, 'gallery/photo_detail.html', {'photo': photo})