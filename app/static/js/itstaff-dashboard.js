/* ==========================================================================
   IT Staff Dashboard JavaScript
   ========================================================================== */

// Check authentication
if (!requireAuth()) { }
const user = getCurrentUser();
// Relaxed role check for 'itstaff' vs 'it_staff'
if (!user || (user.role !== 'itstaff' && user.role !== 'it_staff')) {
    alert('Access denied. IT Staff only.');
    redirectToDashboard();
}

let cachedTickets = [];

document.addEventListener('DOMContentLoaded', async function () {
    await initializeDashboard();
    await loadTickets();
    setupEventListeners();
});

async function initializeDashboard() {
    try {
        const response = await fetch('/api/v1/users/me', {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (response.ok) {
            const userData = await response.json();

            // Sync global user object for logic consistency
            Object.assign(user, userData);

            // Set user name
            document.getElementById('userName').textContent = userData.full_name;
            document.getElementById('welcomeMessage').textContent = `Welcome Back, ${userData.full_name}!`;

            // Set user avatar initials
            const initials = userData.full_name.split(' ').map(n => n[0]).join('').toUpperCase();
            document.getElementById('userAvatar').textContent = initials;
        } else {
            // Fallback
            document.getElementById('userName').textContent = user.name;
            document.getElementById('welcomeMessage').textContent = `Welcome Back, ${user.name}!`;
            const initials = user.name.split(' ').map(n => n[0]).join('').toUpperCase();
            document.getElementById('userAvatar').textContent = initials;
        }
    } catch (e) {
        console.warn("Profile sync error", e);
        // Fallback display
        document.getElementById('userName').textContent = user.name;
        document.getElementById('welcomeMessage').textContent = `Welcome Back, ${user.name}!`;
    }

    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('currentDate').textContent = new Date().toLocaleDateString('en-US', options);
}

function setupEventListeners() {
    document.getElementById('updateTicketForm').addEventListener('submit', handleUpdateTicket);
    document.getElementById('searchTickets').addEventListener('input', handleSearch);
}

async function getTickets() {
    const token = getAuthToken();
    try {
        // Add timestamp to prevent caching
        const response = await fetch(`/api/v1/tickets?ts=${Date.now()}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) return await response.json();
    } catch (e) {
        console.error("Failed to fetch tickets", e);
    }
    return [];
}

async function loadTickets() {
    cachedTickets = await getTickets();
    await updateKPIs();
    // Default view: All tickets
    displayTickets(cachedTickets, 'all');
}

function formatTicketId(id) {
    return `T-${1000 + parseInt(id)}`;
}

async function updateKPIs() {
    try {
        const token = getAuthToken();
        const response = await fetch('/api/v1/analytics/it-dashboard', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const data = await response.json();
            document.getElementById('assignedTickets').textContent = data.assigned_tickets;
            document.getElementById('inProgressTickets').textContent = data.in_progress_tickets;
            document.getElementById('resolvedTickets').textContent = data.resolved_tickets;
            document.getElementById('slaBreaches').textContent = data.sla_breaches;
        }
    } catch (e) {
        console.error("Failed to update IT KPIs", e);
    }
}

function updatePerformanceChart(meData) {
    // [Removed as requested]
}

function displayTickets(tickets, viewMode = 'all') {
    const tbody = document.getElementById('ticketsTableBody');
    if (tickets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center py-5"><div class="text-muted"><i class="fas fa-inbox fa-3x mb-3"></i><p>No tickets assigned</p></div></td></tr>';
        return;
    }

    const priorityOrder = { 'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1 };
    tickets.sort((a, b) => {
        const diff = priorityOrder[b.priority] - priorityOrder[a.priority];
        return diff !== 0 ? diff : new Date(b.createdAt) - new Date(a.createdAt);
    });

    tbody.innerHTML = tickets.map(t => {
        // Robust check matching filterTickets logic
        const userName = (user.full_name || user.name || "").toLowerCase();

        // KEY LOGIC: Only consider it "Assigned To Me" (for UI purposes) if we are in 'my-assignments' view.
        // If we are in Dashboard ('all'), we want to treat it as "Occupied" (Yellow Approach Button) regardless of owner.
        // Handle "Team : Name" format
        const assignedLower = t.assignedTo ? t.assignedTo.toLowerCase() : "";
        const isAssignedToMe = (viewMode === 'my-assignments') && t.assignedTo &&
            (assignedLower === userName || assignedLower.endsWith(' : ' + userName));

        // Logic: Show "Approach" if it's NOT assigned to me (in this context), and NOT Closed/Resolved.
        const canApproach = !isAssignedToMe && t.status !== 'Closed' && t.status !== 'Resolved';

        return `
        <tr>
            <td><strong>${formatTicketId(t.id)}</strong></td>
            <td>${t.title || t.subject}</td>
            <td><span class="badge bg-secondary">${t.category}</span></td>
            <td><span class="priority-badge priority-${t.priority.toLowerCase()}">${t.priority}</span></td>
            <td>${t.createdByName || 'Unknown'}</td>
            <td><span class="status-badge status-${t.status.toLowerCase().replace(' ', '-')}">${t.status}</span></td>
            <td>${timeAgo(t.createdAt)}</td>
            <td>
                <div class="d-flex gap-2">
                    <a href="/ticket/${t.id}" class="btn btn-sm btn-view" title="View Details"><i class="fas fa-eye"></i></a>
                    ${canApproach ?
                `<button class="btn btn-sm ${t.assignedToId ? 'btn-warning text-dark' : 'btn-outline-success'}" 
                        onclick="openApproachModal(${t.id})" 
                        title="${t.assignedToId ? 'Ticket Approached' : 'Approach Ticket'}" 
                        style="border-width: 2px; font-weight: 600;"
                        ${t.assignedToId ? 'disabled' : ''}>
                            <i class="fas ${t.assignedToId ? 'fa-user-check' : 'fa-hand-holding-medical'} me-1"></i> 
                            ${t.assignedToId ? 'Approached' : 'Approach'}
                        </button>` :
                (isAssignedToMe ? `<button class="btn btn-sm btn-primary-custom" onclick="showUpdateModal('${t.id}')"><i class="fas fa-edit"></i> Update</button>` : `<button class="btn btn-sm btn-secondary" disabled><i class="fas fa-lock"></i></button>`)
            }
                </div>
            </td>
        </tr>
    `}).join('');
}

// Helper to safely get or create modal instance
function getModal(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    return bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el);
}

// Open Confirmation Modal
function openApproachModal(ticketId) {
    document.getElementById('approachTicketId').value = ticketId;
    const modal = getModal('confirmApproachModal');
    modal.show();
}

// Actual Action triggerd by Modal Button
async function confirmApproachAction() {
    // Disable button to prevent double clicks
    const btn = document.querySelector('#confirmApproachModal .btn-success');
    if (btn) btn.disabled = true;

    const ticketId = document.getElementById('approachTicketId').value;
    const modal = getModal('confirmApproachModal');

    try {
        const token = getAuthToken();
        const response = await fetch(`/api/v1/tickets/${ticketId}/claim`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        // Always hide modal immediately
        modal.hide();

        if (response.ok) {
            // Success
            loadTickets();
        } else {
            const data = await response.json();
            // Delay to allow main modal to close visually
            setTimeout(() => {
                if (response.status === 409) {
                    // Conflict - Already Taken
                    const conflictModal = getModal('concurrencyModal');
                    conflictModal.show();
                    loadTickets();
                } else if (response.status === 400 && data.error && data.error.includes("Workload")) {
                    // Limit Reached
                    const workloadModal = getModal('workloadLimitModal');
                    workloadModal.show();
                } else if (response.status === 400 && data.error && data.error.includes("withdrawn")) {
                    // Withdrawn
                    const withdrawnModal = getModal('ticketWithdrawnModal');
                    withdrawnModal.show();
                    loadTickets();
                } else {
                    alert(data.error || "Failed to approach ticket");
                }
            }, 300);
        }
    } catch (e) {
        console.error("Approach error:", e);
        modal.hide();
        alert("An error occurred while trying to approach the ticket.");
    } finally {
        if (btn) btn.disabled = false;
    }
}

function filterTickets(status) {
    const user = getCurrentUser();
    let filtered;
    let viewMode = 'all';

    if (status === 'all') {
        // Show all for team
        filtered = cachedTickets;
    } else if (status === 'my-assignments') {
        viewMode = 'my-assignments';
        // Strict filtering for "My Assignments"
        const userName = (user.full_name || user.name || "").toLowerCase();

        filtered = cachedTickets.filter(t => {
            if (!t.assignedTo) return false;
            // Case insensitive comparison, handling "Team : Name" format
            const assignedLower = t.assignedTo.toLowerCase();
            return assignedLower === userName || assignedLower.endsWith(' : ' + userName);
        });
    } else {
        filtered = cachedTickets.filter(t => t.status === status);
    }

    // Pass viewMode to displayTickets
    displayTickets(filtered, viewMode);

    if (window.event && window.event.target) {
        document.querySelectorAll('.nav-link-item').forEach(link => link.classList.remove('active'));
        const clicked = window.event.target.closest('.nav-link-item');
        if (clicked) clicked.classList.add('active');
    }
}

function handleSearch(e) {
    const term = e.target.value.toLowerCase();
    const filtered = cachedTickets.filter(t =>
        formatTicketId(t.id).toLowerCase().includes(term) ||
        String(t.id).includes(term) ||
        (t.title && t.title.toLowerCase().includes(term)) ||
        (t.createdByName && t.createdByName.toLowerCase().includes(term))
    );
    displayTickets(filtered);
}

function showUpdateModal(ticketId) {
    const ticket = cachedTickets.find(t => t.id == ticketId);
    if (!ticket) return;

    // Check if already resolved
    if (ticket.status === 'Resolved') {
        const modal = getModal('alreadyResolvedModal');
        modal.show();
        return;
    }

    document.getElementById('updateTicketId').value = ticketId;
    document.getElementById('updateTicketTitle').textContent = `Update ${formatTicketId(ticketId)}`;

    // Strict requirement: Only show "Resolved" option
    const select = document.getElementById('updateStatus');
    select.innerHTML = '<option value="Resolved">Resolved</option>';
    select.value = 'Resolved';

    const modal = getModal('updateTicketModal');
    modal.show();
}

async function handleUpdateTicket(e) {
    e.preventDefault();
    const btn = document.querySelector('#updateTicketForm button[type="submit"]');
    if (btn) btn.disabled = true;

    const ticketId = document.getElementById('updateTicketId').value;
    const newStatus = document.getElementById('updateStatus').value;
    const note = document.getElementById('updateNote').value;

    try {
        const token = getAuthToken();
        const response = await fetch(`/api/v1/tickets/${ticketId}`, {
            method: 'PUT', // or PATCH
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ status: newStatus })
        });

        if (note) {
            // Post comment separately
            await fetch(`/api/v1/tickets/${ticketId}/comments`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ text: `[Status Update] ${note}` })
            });
        }

        if (response.ok) {
            const modal = getModal('updateTicketModal');
            modal.hide();
            document.getElementById('updateTicketForm').reset();
            loadTickets();

            // Show Success Toast if resolved
            if (newStatus === 'Resolved') {
                showToast('Ticket resolved successfully', 'success');
            } else {
                showToast('Ticket updated successfully', 'success');
            }
        } else {
            showToast('Failed to update ticket', 'error');
        }
    } catch (e) {
        console.error(e);
        alert('Error updating ticket');
    } finally {
        if (btn) btn.disabled = false;
    }
}

// Show Toast Notification
function showToast(message, type = 'info') {
    // Create container if it doesn't exist
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 12px;
        `;
        document.body.appendChild(container);
    }

    // Create toast element
    const toast = document.createElement('div');

    // Colors based on type
    const colors = {
        success: { bg: 'rgba(16, 185, 129, 0.9)', icon: 'check-circle' },
        error: { bg: 'rgba(239, 68, 68, 0.9)', icon: 'exclamation-circle' },
        info: { bg: 'rgba(59, 130, 246, 0.9)', icon: 'info-circle' }
    };
    const style = colors[type] || colors.info;

    toast.style.cssText = `
        background: ${style.bg};
        color: white;
        padding: 12px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 10px;
        transform: translateX(120%);
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(8px);
        min-width: 300px;
    `;

    toast.innerHTML = `
        <i class="fas fa-${style.icon}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => {
        toast.style.transform = 'translateX(0)';
    });

    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.transform = 'translateX(120%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('active');
    document.getElementById('sidebarOverlay').classList.toggle('active');
}

function timeAgo(dateString) {
    if (!dateString) return 'Unknown';
    if (!dateString.endsWith('Z') && !dateString.includes('+')) dateString += 'Z';
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    // ... simple time ago logic
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor((seconds + 1) / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor((seconds + 1) / 3600)}h ago`;
    return `${Math.floor((seconds + 1) / 86400)}d ago`;
}