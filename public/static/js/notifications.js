/**
 * Notifications Management & Periodic Polling
 */

document.addEventListener('DOMContentLoaded', () => {
  setupNotificationCenter();
});

function setupNotificationCenter() {
  const badge = document.getElementById('notification-badge');
  const countEl = document.getElementById('notification-count');
  const listEl = document.getElementById('notification-list');
  const markAllBtn = document.getElementById('mark-all-read-btn');

  // Fetch notifications
  function loadNotifications() {
    fetch('/api/notifications')
      .then(res => res.json())
      .then(data => {
        const count = data.unread_count || 0;
        if (badge) {
          badge.style.display = count > 0 ? 'block' : 'none';
        }
        if (countEl) {
          countEl.innerText = count;
        }

        if (listEl && data.notifications) {
          if (data.notifications.length === 0) {
            listEl.innerHTML = `
              <div class="p-4 text-center text-muted" style="font-size: 0.85rem;">
                <i class="fa-regular fa-bell-slash mb-2" style="font-size: 1.5rem; opacity: 0.5;"></i>
                <div>No recent notifications</div>
              </div>
            `;
            return;
          }

          let html = '';
          data.notifications.forEach(n => {
            const isUnread = n.is_read === 0;
            const bgClass = isUnread ? 'style="background: var(--bg-surface-secondary);"' : '';
            const unreadDot = isUnread ? '<span style="width: 7px; height: 7px; border-radius: 50%; background: var(--primary); display: inline-block;"></span>' : '';

            html += `
              <div class="p-3 border-bottom d-flex align-items-start gap-2 notification-item" ${bgClass} style="font-size: 0.85rem; border-color: var(--border-color) !important;">
                <div style="flex: 1;">
                  <div class="d-flex align-items-center justify-content-between mb-1">
                    <span class="fw-semibold text-main">${n.title}</span>
                    ${unreadDot}
                  </div>
                  <div class="text-muted mb-1" style="font-size: 0.8rem; line-height: 1.35;">${n.message}</div>
                  <div class="d-flex align-items-center justify-content-between">
                    <span class="text-muted" style="font-size: 0.72rem;">${n.created_at}</span>
                    ${n.link && n.link !== '#' ? `<a href="${n.link}" class="text-primary fw-medium" style="font-size: 0.75rem;">View →</a>` : ''}
                  </div>
                </div>
              </div>
            `;
          });
          listEl.innerHTML = html;
        }
      })
      .catch(err => console.error('Error fetching notifications:', err));
  }

  // Initial load
  loadNotifications();

  // Periodic polling every 25 seconds for timely dashboard updates
  setInterval(loadNotifications, 25000);

  // Mark all read
  if (markAllBtn) {
    markAllBtn.addEventListener('click', (e) => {
      e.preventDefault();
      fetch('/api/notifications/read-all', { method: 'POST' })
        .then(res => res.json())
        .then(() => {
          loadNotifications();
          showToast('Updated', 'All notifications marked as read.', 'info');
        });
    });
  }
}
