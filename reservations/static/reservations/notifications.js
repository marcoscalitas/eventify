function checkNotifications() {
    safeFetch('/api/notifications')
        .then(data => {
            const badge = document.getElementById('notifBadge');
            if (!badge) return;
            if (data.unread_count <= 0) {
                badge.style.display = 'none';
                return;
            }
            badge.textContent = data.unread_count > 99 ? '99+' : data.unread_count;
            badge.style.display = 'inline-flex';
        })
        .catch(() => {});
}
checkNotifications();
setInterval(checkNotifications, 30000);
