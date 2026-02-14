document.addEventListener('DOMContentLoaded', function() {
    const editBtn = document.getElementById('trashEditBtn');
    const controlBar = document.getElementById('trashControlBar');
    const trashBtns = document.querySelectorAll('.trash-btns');
    const checkboxWrappers = document.querySelectorAll('.edit-checkbox-wrapper');
    const checkboxes = document.querySelectorAll('.photo-select-checkbox');
    let isEditMode = false;

    // 1. 편집 모드 토글
    editBtn.addEventListener('click', () => {
        isEditMode = !isEditMode;
        controlBar.style.display = isEditMode ? 'flex' : 'none';
        
        trashBtns.forEach(btns => btns.style.display = isEditMode ? 'none' : 'flex');
        checkboxWrappers.forEach(w => w.style.display = isEditMode ? 'block' : 'none');

        if (!isEditMode) exitTrashEdit();
    });

    // 2. 체크박스 선택 이벤트 (카드 강조 및 숫자 업데이트)
    checkboxes.forEach(cb => {
        cb.addEventListener('change', () => {
            const count = document.querySelectorAll('.photo-select-checkbox:checked').length;
            document.getElementById('selectedCount').textContent = count;
            cb.closest('.trash-card').classList.toggle('selected', cb.checked);
        });
    });
});

// 휴지통 전체 비우기 함수
async function emptyTrashAll() {
    if (!confirm('휴지통의 모든 사진을 영구 삭제하시겠습니까?\n이 작업은 절대 되돌릴 수 없습니다.')) {
        return;
    }

    try {
        const response = await fetch('/gallery/photos/empty-trash/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': CSRF_TOKEN,
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.success) {
            alert('휴지통을 완전히 비웠습니다.');
            location.reload();
        } else {
            alert('비우기 실패: ' + (data.error || '알 수 없는 오류'));
        }
    } catch (error) {
        console.error('Empty trash error:', error);
        alert('서버와 통신 중 오류가 발생했습니다.');
    }
}

// 일괄 복구 함수
async function bulkRestore() {
    const selectedIds = Array.from(document.querySelectorAll('.photo-select-checkbox:checked')).map(cb => cb.value);
    if (selectedIds.length === 0) return alert('사진을 선택해주세요.');

    const response = await fetch('/gallery/photos/bulk-restore/', {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF_TOKEN, 'Content-Type': 'application/json' },
        body: JSON.stringify({ photoIds: selectedIds })
    });

    if ((await response.json()).success) location.reload();
}

// 일괄 영구 삭제 함수
async function bulkPermanentDelete() {
    const selectedIds = Array.from(document.querySelectorAll('.photo-select-checkbox:checked')).map(cb => cb.value);
    if (selectedIds.length === 0) return alert('사진을 선택해주세요.');

    if (!confirm(`선택한 ${selectedIds.length}장의 사진을 영구 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.`)) return;

    const response = await fetch('/gallery/photos/bulk-permanent-delete/', {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF_TOKEN, 'Content-Type': 'application/json' },
        body: JSON.stringify({ photoIds: selectedIds })
    });

    if ((await response.json()).success) location.reload();
}

function exitTrashEdit() {
    document.querySelectorAll('.photo-select-checkbox').forEach(cb => {
        cb.checked = false;
        cb.closest('.trash-card').classList.remove('selected');
    });
    document.getElementById('selectedCount').textContent = '0';
    // 모드 종료 시 페이지를 새로고침하거나 UI를 수동으로 복구
    location.reload(); 
}

function restorePhoto(photoId, csrfToken) {
    if (!confirm('사진을 복구하시겠습니까?')) return;
    fetch(`/gallery/trash/${photoId}/restore/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken }
    })
    .then(res => res.json())
    .then(data => { if(data.success) location.reload(); });
}

function permanentDelete(photoId, csrfToken) {
    if (!confirm('영구 삭제하면 되돌릴 수 없습니다. 삭제하시겠습니까?')) return;
    fetch(`/gallery/trash/${photoId}/`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': csrfToken }
    })
    .then(res => res.json())
    .then(data => { if(data.success) location.reload(); });
}