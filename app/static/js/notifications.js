/* ==========================================================================
   Notification System JavaScript
   Handles fetching, displaying, and real-time updates for notifications
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {
    if (requireAuth()) {
        setupNotifications();
    }
});

function setupNotifications() {
    // 1. Inject Bell Icon if not present (or bind to existing)
    // We assume the HTML will have a container with class 'header-actions'
    // We will append the bell button there if it doesn't exist, or we can just expect it in HTML.
    // For now, let's look for #notificationDropdownToggle

    const bellBtn = document.getElementById('notificationDropdownToggle');
    if (!bellBtn) {
        console.warn('Notification bell button not found. Notifications UI might be missing.');
        return;
    }

    // 2. Fetch Initial Notifications
    fetchNotifications();

    // 3. Listen for Socket Events
    if (typeof socket !== 'undefined') {
        socket.on('new_notification', function (data) {
            // Check if notification is for current user
            const currentUser = getCurrentUser();
            if (currentUser && data.user_id === currentUser.id) {
                handleNewNotification(data);
            }
        });
    }
}

async function fetchNotifications() {
    try {
        const response = await fetch('/api/v1/notifications/', {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (response.ok) {
            const data = await response.json();
            updateNotificationUI(data.notifications, data.unread_count);
        }
    } catch (e) {
        console.error("Failed to fetch notifications", e);
    }
}

function updateNotificationUI(notifications, unreadCount) {
    // Update Badge
    const badge = document.getElementById('notificationBadge');
    if (badge) {
        if (unreadCount > 9) {
            badge.textContent = '9+';
        } else {
            badge.textContent = unreadCount;
        }
        badge.style.display = unreadCount > 0 ? 'block' : 'none';
    }

    // Switch Bell Behavior: Dropdown vs Modal
    const bellBtn = document.getElementById('notificationDropdownToggle');
    const list = document.getElementById('notificationList');

    if (notifications.length === 0) {
        // Case: No Notifications -> Show Modal
        if (bellBtn) {
            bellBtn.removeAttribute('data-bs-toggle'); // Disable dropdown
            bellBtn.onclick = function (e) {
                e.preventDefault();
                e.stopPropagation();
                // Show Modal
                const modalEl = document.getElementById('noNotificationsModal');
                if (modalEl) {
                    const modal = new bootstrap.Modal(modalEl);
                    modal.show();
                }
            };
        }
        if (list) {
            list.innerHTML = ''; // Keep empty
        }
    } else {
        // Case: Notifications Exist -> Show Dropdown
        if (bellBtn) {
            bellBtn.setAttribute('data-bs-toggle', 'dropdown');
            bellBtn.onclick = null; // Remove standard click intercept
        }

        if (list) {
            list.innerHTML = notifications.map(n => `
                <li>
                    <a class="dropdown-item ${n.is_read ? '' : 'fw-bold bg-light'}" href="#" onclick="markAsRead(${n.id}, event)">
                        <div class="d-flex align-items-center">
                            <div class="flex-grow-1">
                                <h6 class="mb-0 text-wrap small">${n.title}</h6>
                                <p class="mb-0 text-muted small text-wrap">${n.message}</p>
                                <small class="text-secondary" style="font-size: 0.7rem;">${timeAgo(n.created_at)}</small>
                            </div>
                            ${!n.is_read ? '<span class="dot bg-primary ms-2" style="width: 8px; height: 8px; border-radius: 50%;"></span>' : ''}
                        </div>
                    </a>
                </li>
            `).join('');

            // Optional: Add Clear All button at the bottom of dropdown
            // list.innerHTML += '<li><hr class="dropdown-divider"></li><li><a class="dropdown-item text-center small text-danger" href="/profile">View All & Clear</a></li>';
        }
    }
}

function handleNewNotification(notification) {
    // Play sound?
    // Show Toast
    showToast(`🔔 ${notification.title}: ${notification.message}`);

    // Refresh List (or append manually)
    fetchNotifications();
}

async function markAsRead(notificationId, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation(); // Keep dropdown open? Or let it close.
    }

    try {
        await fetch(`/api/v1/notifications/${notificationId}/read`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        // Refresh to update UI (remove bold, update badge)
        fetchNotifications();
    } catch (e) {
        console.error("Failed to mark as read", e);
    }
}

// Clear function for Profile Page
window.clearNotifications = async function () {
    const btn = event.target.closest('button');

    // Check if there are notifications to clear
    try {
        const response = await fetch('/api/v1/notifications/', {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });
        if (response.ok) {
            const data = await response.json();
            if (data.notifications.length === 0) {
                // Zero notifications -> Show "No Notifications" Modal
                const noNotifModal = new bootstrap.Modal(document.getElementById('noNotificationsModal'));
                noNotifModal.show();
                return;
            }
        }
    } catch (e) {
        console.error("Check failed", e);
    }

    // Has notifications -> Show Confirmation Modal
    const confirmModal = new bootstrap.Modal(document.getElementById('clearNotificationsModal'));
    confirmModal.show();
}

window.confirmClearNotifications = async function () {
    // Hide Modal
    const modalEl = document.getElementById('clearNotificationsModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    modal.hide();

    try {
        const response = await fetch('/api/v1/notifications/', {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (response.ok) {
            showToast('All notifications cleared successfully');
            fetchNotifications(); // Update UI
        } else {
            showToast('Failed to clear notifications', 'error');
        }
    } catch (e) {
        console.error("Failed to clear notifications", e);
        showToast('Error occurred', 'error');
    }
}
