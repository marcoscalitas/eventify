document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.cancel-res-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!confirm('Cancel this reservation?')) return;
            postAction(btn, `/api/event/${btn.dataset.eventId}/cancel`)
            .then(data => {
                showToast(data.message);
                document.getElementById(`res-${btn.dataset.resId}`).remove();
            });
        });
    });
});
