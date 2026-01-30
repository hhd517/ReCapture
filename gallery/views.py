from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Photo

@login_required
def photo_detail(request, pk):
    # 본인의 사진만 볼 수 있도록 user 필터링 추가
    photo = get_object_or_404(Photo, pk=pk, user=request.user)
    
    if request.method == 'POST':
        # 메모 업데이트 및 북마크 토글
        new_memo = request.POST.get('memo')
        is_bookmarked = request.POST.get('is_bookmarked') == 'on'
        
        photo.memo = new_memo
        photo.is_bookmarked = is_bookmarked
        photo.save()
        
        return redirect('gallery:photo_detail', pk=photo.pk)

    return render(request, 'gallery/photo_detail.html', {'photo': photo})

@login_required
def trash_list(request):
    # 휴지통에 버려진 사진들만 조회
    trashed_photos = Photo.objects.filter(user=request.user, is_trashed=True).order_set('-trashed_at')
    return render(request, 'gallery/trash_list.html', {'photos': trashed_photos})

@login_required
def toggle_bookmark(request, pk):
    # 목록 페이지에서도 바로 북마크를 껐다 켰다 할 수 있는 기능
    photo = get_object_or_404(Photo, pk=pk, user=request.user)
    photo.is_bookmarked = not photo.is_bookmarked
    photo.save()
    return redirect(request.META.get('HTTP_REFERER', 'gallery:photo_list'))