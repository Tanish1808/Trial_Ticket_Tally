/* ==========================================================================
   Profile Page JavaScript
   User profile, settings, preferences, and activity
   ========================================================================== */

// Check authentication
if (!requireAuth()) {
    // Will redirect if not authenticated
}

const currentUser = getCurrentUser();

// Initialize page
document.addEventListener('DOMContentLoaded', function () {
    if (!currentUser) {
        alert('Session expired. Please login again.');
        window.location.href = '/login';
        return;
    }

    loadProfile();
    loadRecentActivity();
    // setupPreferences called inside loadProfile now
});

// Load profile information
async function loadProfile() {
    try {
        const response = await fetch('/api/v1/users/me', {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (response.ok) {
            const userData = await response.json();

            // Set avatar initials
            const initials = userData.full_name.split(' ').map(n => n[0]).join('').toUpperCase();
            document.getElementById('profileAvatar').textContent = initials;

            // Set name and role
            document.getElementById('profileName').textContent = userData.full_name;

            // Format role name
            let roleDisplay = userData.role.charAt(0).toUpperCase() + userData.role.slice(1);
            if (userData.role === 'it_staff') { // API uses 'it_staff'
                roleDisplay = 'IT Staff';
            }
            document.getElementById('profileRole').textContent = roleDisplay;

            // Personal Information
            document.getElementById('infoName').textContent = userData.full_name;
            document.getElementById('infoEmail').textContent = userData.email;
            document.getElementById('infoRole').textContent = roleDisplay;

            // Show department for employees
            if (userData.department) {
                document.getElementById('infoDepartment').textContent = userData.department;
                document.getElementById('infoDepartmentContainer').style.display = 'block';
            } else {
                document.getElementById('infoDepartmentContainer').style.display = 'none';
            }

            // Show team for IT staff
            // Note: /me endpoint returns team_id. Use that or fetch team name if needed. 
            // The API response shows 'team_id'. If we need Name, we might need to adjust API or just show ID/generic.
            // Wait, looking at user_routes.py get_me: "team_id": g.user.team_id.
            // But get_all_users returns "team": u.team.name.
            // The profile.html expects a team name.
            // Let's rely on info loaded from 'tickets' or just hide if null.
            // For now, if just team_id, hide or show. 
            // Actually, I can assume team name isn't critical for "Errorless" stats, keeping it simple.
            // OR I can quickly patch user_routes.py to return team name. 
            // Let's patch user_routes.py first? No, user said "asap".
            // I'll show "Team Member" or similar if ID exists, or just hide.
            // Actually get_me returns team_id.
            if (userData.team_id) {
                document.getElementById('infoTeam').textContent = `Team #${userData.team_id}`; // Fallback
                document.getElementById('infoTeamContainer').style.display = 'block';
            } else {
                document.getElementById('infoTeamContainer').style.display = 'none';
            }

            // Member since
            const memberSince = userData.created_at || new Date().toISOString();
            document.getElementById('infoMemberSince').textContent = formatDate(memberSince);

            // Trigger Stat Load with correct role from DB
            loadStats(userData.role);

            // Init Preferences
            initPreferencesUI(userData.preferences);
        }
    } catch (e) {
        console.error("Failed to load profile", e);
    }
}

// Load statistics based on role
async function loadStats(userRole) {
    const statsContainer = document.getElementById('profileStats');
    statsContainer.innerHTML = '<p class="text-white">Loading stats...</p>';

    try {
        if (userRole === 'admin') {
            // Admin stats from Analytics API
            const response = await fetch('/api/v1/analytics/dashboard', {
                headers: { 'Authorization': `Bearer ${getAuthToken()}` }
            });

            if (response.ok) {
                const data = await response.json();
                statsContainer.innerHTML = `
                    <div class="stat-card">
                        <div class="stat-value">${data.total_tickets}</div>
                        <div class="stat-label">System Tickets</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${data.open_tickets}</div>
                        <div class="stat-label">Open Tickets</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${data.total_users}</div>
                        <div class="stat-label">Total Users</div>
                    </div>
                `;
            }
        } else {
            // Employee & IT Staff stats from Tickets API
            const response = await fetch('/api/v1/tickets', {
                headers: { 'Authorization': `Bearer ${getAuthToken()}` }
            });

            if (response.ok) {
                const tickets = await response.json();

                if (userRole === 'employee') {
                    // Employee stats - tickets created by me
                    // /api/v1/tickets for employee returns THEIR tickets (created by them)
                    const totalTickets = tickets.length;
                    const openTickets = tickets.filter(t => t.status === 'Open').length;
                    const resolvedTickets = tickets.filter(t => t.status === 'Resolved').length;

                    statsContainer.innerHTML = `
                        <div class="stat-card">
                            <div class="stat-value">${totalTickets}</div>
                            <div class="stat-label">Total Tickets</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${openTickets}</div>
                            <div class="stat-label">Open Tickets</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${resolvedTickets}</div>
                            <div class="stat-label">Resolved Tickets</div>
                        </div>
                    `;
                } else if (userRole === 'it_staff' || userRole === 'itstaff') {
                    // IT Staff stats - tickets assigned to their team
                    // /api/v1/tickets for IT Staff returns assigned tickets
                    const assignedTickets = tickets.length;
                    const inProgress = tickets.filter(t => t.status === 'In Progress').length;
                    const resolvedByMe = tickets.filter(t => t.status === 'Resolved').length; // Approximation

                    statsContainer.innerHTML = `
                        <div class="stat-card">
                            <div class="stat-value">${assignedTickets}</div>
                            <div class="stat-label">Assigned Tickets</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${inProgress}</div>
                            <div class="stat-label">In Progress</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${resolvedByMe}</div>
                            <div class="stat-label">Resolved</div>
                        </div>
                    `;
                }
            }
        }
    } catch (e) {
        console.error("Failed to load stats", e);
        statsContainer.innerHTML = '<p class="text-white">Failed to load statistics</p>';
    }
}

// Load recent activity
async function loadRecentActivity() {
    const container = document.getElementById('recentActivity');
    container.innerHTML = '<p class="text-muted p-3">Loading activity...</p>';

    try {
        const response = await fetch('/api/v1/tickets', {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (response.ok) {
            const tickets = await response.json();

            // Sort by date desc
            tickets.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

            const activities = tickets.slice(0, 5).map(ticket => ({
                icon: 'fa-ticket-alt',
                title: `Ticket: ${ticket.title}`,
                time: ticket.createdAt ? timeAgo(ticket.createdAt) : 'Recently',
                color: getStatusColor(ticket.status)
            }));

            if (activities.length === 0) {
                container.innerHTML = '<div class="p-3 text-muted">No recent activity</div>';
                return;
            }

            container.innerHTML = activities.map(activity => `
                <div class="activity-item">
                    <div class="activity-icon" style="background: ${activity.color};">
                        <i class="fas ${activity.icon}"></i>
                    </div>
                    <div class="activity-content">
                        <div class="activity-title">${activity.title}</div>
                        <div class="activity-time">${activity.time}</div>
                    </div>
                </div>
            `).join('');
        }
    } catch (e) {
        console.error("Failed to load activity", e);
        container.innerHTML = '<p class="text-danger p-3">Error loading activity</p>';
    }
}

// Get status color
function getStatusColor(status) {
    const colors = {
        'Open': '#3b82f6',
        'In Progress': '#f59e0b',
        'Resolved': '#10b981',
        'Closed': '#6b7280'
    };
    return colors[status] || '#3b82f6';
}

// Setup preferences
function setupPreferences() {
    // We rely on currentUser (which might be stale) or the data loaded in loadProfile
    // To ensure we have latest, let's fetch from API or use the ones from loadProfile if we passed them
    // But loadProfile is async. 
    // Let's just hook up the change listeners to save to API.
    // Initialization should happen after loadProfile.
}

// Save preference to API
async function savePreference(key, value) {
    try {
        const preferences = {};
        preferences[key] = value;

        await fetch('/api/v1/users/me', {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({ preferences })
        });
    } catch (e) {
        console.error("Failed to save preference", e);
    }
}

// Initialize Preferences UI from Data
function initPreferencesUI(preferences) {
    if (!preferences) preferences = {};

    // Dark Mode
    const darkModeSwitch = document.getElementById('darkModeSwitch');
    const currentTheme = localStorage.getItem('ticket-tally-theme') || 'light';
    darkModeSwitch.checked = currentTheme === 'dark';

    darkModeSwitch.addEventListener('change', function () {
        const newTheme = this.checked ? 'dark' : 'light';
        localStorage.setItem('ticket-tally-theme', newTheme);
        document.documentElement.setAttribute('data-theme', newTheme);
        updateThemeIcon(newTheme);
    });

    // Email Notifications
    const emailSwitch = document.getElementById('emailNotifications');
    // Default to true if not set
    const emailPref = preferences.email_notifications !== undefined ? preferences.email_notifications : true;
    emailSwitch.checked = emailPref;
    localStorage.setItem('email-notifications', emailPref); // Sync

    emailSwitch.addEventListener('change', function () {
        const val = this.checked;
        localStorage.setItem('email-notifications', val);
        savePreference('email_notifications', val);
        showToast(val ? 'Email notifications enabled' : 'Email notifications disabled');
    });

    // Auto Refresh
    const refreshSwitch = document.getElementById('autoRefresh');
    const refreshPref = preferences.auto_refresh !== undefined ? preferences.auto_refresh : true;
    refreshSwitch.checked = refreshPref;
    localStorage.setItem('auto-refresh', refreshPref);

    refreshSwitch.addEventListener('change', function () {
        const val = this.checked;
        localStorage.setItem('auto-refresh', val);
        savePreference('auto_refresh', val);
        showToast(val ? 'Auto-refresh enabled' : 'Auto-refresh disabled');
    });

    // Show Closed
    const closedSwitch = document.getElementById('showClosed');
    const closedPref = preferences.show_closed !== undefined ? preferences.show_closed : false;
    closedSwitch.checked = closedPref;
    localStorage.setItem('show-closed', closedPref);

    closedSwitch.addEventListener('change', function () {
        const val = this.checked;
        localStorage.setItem('show-closed', val);
        savePreference('show_closed', val);
        showToast(val ? 'Showing closed tickets' : 'Hiding closed tickets');
    });

    // Theme observer
    const observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
                const newTheme = document.documentElement.getAttribute('data-theme');
                if (darkModeSwitch) darkModeSwitch.checked = newTheme === 'dark';
                updateThemeIcon(newTheme);
            }
        });
    });

    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme']
    });
}

// Update theme icon
function updateThemeIcon(theme) {
    const icon = document.querySelector('#darkModeToggle i');
    if (icon) {
        icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

// Edit profile
function editProfile() {
    document.getElementById('editFullName').value = currentUser.name || document.getElementById('profileName').textContent;

    // Show department field only if applicable (e.g. employee)
    const deptDiv = document.getElementById('editDepartmentContainer');
    const roleElem = document.getElementById('profileRole');
    if (roleElem.textContent.trim() === 'Employee') {
        deptDiv.style.display = 'block';
        document.getElementById('editDepartment').value = document.getElementById('infoDepartment').textContent !== '-' ?
            document.getElementById('infoDepartment').textContent : '';
    } else {
        deptDiv.style.display = 'none';
    }

    const modal = new bootstrap.Modal(document.getElementById('editProfileModal'));
    modal.show();
}

// Handle Profile Update Submission
document.getElementById('editProfileForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const fullName = document.getElementById('editFullName').value;
    const department = document.getElementById('editDepartment').value;
    const btn = e.target.querySelector('button[type="submit"]');

    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

    try {
        const response = await fetch('/api/v1/users/me', {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                full_name: fullName,
                department: department
            })
        });

        const data = await response.json();

        if (response.ok) {
            showToast('Profile updated successfully', 'success');
            bootstrap.Modal.getInstance(document.getElementById('editProfileModal')).hide();
            loadProfile(); // Refresh UI

            // Update local storage user name if changed
            if (currentUser) {
                currentUser.name = fullName;
                localStorage.setItem('user', JSON.stringify(currentUser));
            }
        } else {
            showToast(data.error || 'Failed to update profile', 'error');
        }
    } catch (error) {
        console.error('Profile update error:', error);
        showToast('An error occurred', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
});

// Change password
function changePassword() {
    document.getElementById('changePasswordForm').reset();
    const modal = new bootstrap.Modal(document.getElementById('changePasswordModal'));
    modal.show();
}

// Handle Password Change Submission
document.getElementById('changePasswordForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    if (newPassword !== confirmPassword) {
        showToast('New passwords do not match', 'error');
        return;
    }

    const btn = e.target.querySelector('button[type="submit"]');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Changing...';

    try {
        const response = await fetch('/api/v1/users/me/password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });

        const data = await response.json();

        if (response.ok) {
            showToast('Password changed successfully', 'success');
            bootstrap.Modal.getInstance(document.getElementById('changePasswordModal')).hide();
        } else {
            showToast(data.error || 'Failed to change password', 'error');
        }
    } catch (error) {
        console.error('Password change error:', error);
        showToast('An error occurred', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
});

// Open Export Modal
function openExportModal() {
    const modalEl = document.getElementById('exportModal');
    if (modalEl) {
        new bootstrap.Modal(modalEl).show();
    } else {
        console.error('Export modal not found');
        showToast('Error: Export modal missing', 'error');
    }
}

// Bind Export Button
document.addEventListener('DOMContentLoaded', function () {
    const btn = document.getElementById('btn-download-data');
    if (btn) {
        btn.addEventListener('click', openExportModal);
    }
});

// Confirm Export (Global for modal buttons)
window.confirmExport = async function (format) {
    // Close modal
    const modalEl = document.getElementById('exportModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();

    showToast(`Generating ${format.toUpperCase()} export...`, 'info');

    try {
        const token = getAuthToken();
        const response = await fetch(`/api/v1/users/export?format=${format}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ticket_tally_data_${currentUser.id}_${Date.now()}.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
            showToast('Download started', 'success');
        } else {
            showToast('Export failed', 'error');
        }
    } catch (e) {
        console.error("Export error", e);
        showToast('Error exporting data', 'error');
    }
}



// Confirm logout
function confirmLogout() {
    if (confirm('Are you sure you want to logout?')) {
        logout();
    }
}

// Go back to dashboard
// Go back to dashboard
function goBackToDashboard() {
    // Determine Dashboard based on Role
    // Handle both 'it_staff' (backend enum) and 'itstaff' (frontend token sometimes)

    const role = currentUser.role.toLowerCase().replace('_', '');

    if (role === 'employee') {
        window.location.href = '/dashboard/employee';
    } else if (role === 'itstaff') {
        window.location.href = '/dashboard/it-staff';
    } else if (role === 'admin') {
        window.location.href = '/dashboard/admin';
    } else {
        // Fallback
        window.location.href = '/';
    }
}

// Show toast notification
function showToast(message) {
    // Create toast element
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        background: var(--primary-500);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-xl);
        z-index: 9999;
        animation: slideInRight 0.3s ease;
        font-weight: 500;
    `;
    toast.textContent = message;

    document.body.appendChild(toast);

    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// Get tickets from localStorage
function getTickets() {
    const ticketsStr = localStorage.getItem('ticket-tally-tickets');
    return ticketsStr ? JSON.parse(ticketsStr) : [];
}

// Get IT staff
function getStaff() {
    const staffStr = localStorage.getItem('ticket-tally-staff');
    if (staffStr) {
        return JSON.parse(staffStr);
    }
    return [];
}