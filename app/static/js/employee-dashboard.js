/* ==========================================================================
   Employee Dashboard JavaScript
   ========================================================================== */

// Check authentication on page load
if (!requireAuth()) {
    // Will redirect if not authenticated
}

// Global variable to cache tickets for client-side filtering/searching
let cachedTickets = [];

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function () {
    initializeDashboard();
    loadTickets();
    setupEventListeners();
});

// Initialize dashboard
async function initializeDashboard() {
    const user = getCurrentUser();
    if (!user || user.role !== 'employee') {
        alert('Access denied. This dashboard is for employees only.');
        redirectToDashboard();
        return;
    }

    try {
        // Fetch fresh profile data to sync with DB
        const response = await fetch('/api/v1/users/me', {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (response.ok) {
            const userData = await response.json();

            // Set user name (Full Name from DB)
            document.getElementById('userName').textContent = userData.full_name;
            document.getElementById('welcomeMessage').textContent = `Welcome Back, ${userData.full_name}!`; // Full Name

            // Set user avatar initials
            const initials = userData.full_name.split(' ').map(n => n[0]).join('').toUpperCase();
            document.getElementById('userAvatar').textContent = initials;
        } else {
            // Fallback to local storage if API fails (unlikely if auth works)
            console.warn("Failed to sync profile, using local data");
            document.getElementById('userName').textContent = user.name;
            document.getElementById('welcomeMessage').textContent = `Welcome Back, ${user.name}!`;
            const initials = user.name.split(' ').map(n => n[0]).join('').toUpperCase();
            document.getElementById('userAvatar').textContent = initials;
        }
    } catch (e) {
        console.error("Profile sync error", e);
    }

    // Set current date
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('currentDate').textContent = new Date().toLocaleDateString('en-US', options);
}

// Setup event listeners
function setupEventListeners() {
    // Raise ticket form
    document.getElementById('raiseTicketForm').addEventListener('submit', handleRaiseTicket);

    // Search tickets
    document.getElementById('searchTickets').addEventListener('input', handleSearch);

    // Duplicate Ticket Check
    const subjectInput = document.getElementById('ticketSubject');
    if (subjectInput) {
        subjectInput.addEventListener('input', debounce(async (e) => {
            const title = e.target.value.trim();
            const warningEl = document.getElementById('duplicateWarning');

            if (title.length < 5) {
                warningEl.classList.add('d-none');
                return;
            }

            try {
                const token = getAuthToken();
                const response = await fetch('/api/v1/tickets/check-duplicate', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ title: title })
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.exists) {
                        warningEl.querySelector('span').innerHTML =
                            `You already have an open ticket similar to this: <strong>${data.ticket.title}</strong> (ID: T-${1000 + data.ticket.id}).`;
                        warningEl.classList.remove('d-none');
                    } else {
                        warningEl.classList.add('d-none');
                    }
                }
            } catch (error) {
                console.error("Duplicate check failed", error);
            }
        }, 500));
    }
}

// Debounce Utility
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Get tickets from API
async function getTickets() {
    const token = getAuthToken();
    try {
        const response = await fetch('/api/v1/tickets', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (response.ok) {
            return await response.json();
        }
    } catch (e) {
        console.error("Failed to fetch tickets", e);
    }
    return [];
}

// Format Ticket ID
function formatTicketId(id) {
    return `T-${1000 + parseInt(id)}`;
}

// Load and display tickets
async function loadTickets() {
    // Fetch fresh data and update cache
    cachedTickets = await getTickets();

    // Default: Show all active tickets
    filterTickets('all');

    // Update KPI cards - count by status
    updateKPIs(cachedTickets);
}

// Update KPI cards
function updateKPIs(tickets) {
    const total = tickets.length;
    const open = tickets.filter(t => t.status === 'Open').length;
    const inProgress = tickets.filter(t => t.status === 'In Progress').length;
    const resolved = tickets.filter(t => t.status === 'Resolved').length;

    document.getElementById('totalTickets').textContent = total;
    document.getElementById('openTickets').textContent = open;
    document.getElementById('inProgressTickets').textContent = inProgress;
    document.getElementById('resolvedTickets').textContent = resolved;
}

// Display tickets in table
function displayTickets(tickets) {
    const tbody = document.getElementById('ticketsTableBody');
    const emptyState = document.getElementById('emptyState');

    if (!tbody) return;

    if (tickets.length === 0) {
        tbody.innerHTML = '';
        if (emptyState) emptyState.style.display = 'block';
        return;
    }

    if (emptyState) emptyState.style.display = 'none';

    // Sort tickets by priority and date
    const priorityOrder = { 'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1 };
    tickets.sort((a, b) => {
        const priorityDiff = priorityOrder[b.priority] - priorityOrder[a.priority];
        if (priorityDiff !== 0) return priorityDiff;
        return new Date(b.createdAt + (b.createdAt.endsWith('Z') ? '' : 'Z')) - new Date(a.createdAt + (a.createdAt.endsWith('Z') ? '' : 'Z'));
    });

    tbody.innerHTML = tickets.map(ticket => `
        <tr>
            <td><strong>${formatTicketId(ticket.id)}</strong></td>
            <td>${ticket.title || ticket.subject}</td>
            <td><span class="badge bg-secondary">${ticket.category}</span></td>
            <td><span class="priority-badge priority-${ticket.priority.toLowerCase()}">${ticket.priority}</span></td>
            <td><span class="status-badge status-${ticket.status.toLowerCase().replace(' ', '-')}">${ticket.status}</span></td>
            <td>${ticket.assignedTo || '<span class="text-muted">Unassigned</span>'}</td>
            <td>${timeAgo(ticket.createdAt)}</td>
            <td>
                <div class="d-flex gap-2">
                    <a href="/ticket/${ticket.id}" class="btn btn-sm btn-view" title="View Full Details">
                        <i class="fas fa-eye"></i> View
                    </a>
                    <button class="btn btn-sm btn-outline-danger" onclick="downloadTicketPDF('${ticket.id}')" title="Download PDF">
                        <i class="fas fa-file-pdf"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// Filter tickets by status
function filterTickets(status) {
    let filtered;

    if (status === 'all') {
        filtered = cachedTickets.filter(t => t.status !== 'Closed');
    } else {
        filtered = cachedTickets.filter(t => t.status === status);
    }

    displayTickets(filtered);

    // Update active nav link
    if (window.event && window.event.target) {
        document.querySelectorAll('.nav-link-item').forEach(link => {
            link.classList.remove('active');
        });
        const clickedLink = window.event.target.closest('.nav-link-item');
        if (clickedLink) {
            clickedLink.classList.add('active');
        }
    }
}

// Handle search
function handleSearch(e) {
    const searchTerm = e.target.value.toLowerCase();

    // Filter from cachedTickets
    const filtered = cachedTickets.filter(ticket => {
        const formattedId = formatTicketId(ticket.id).toLowerCase();
        const rawId = String(ticket.id);

        return formattedId.includes(searchTerm) ||
            rawId.includes(searchTerm) ||
            (ticket.title && ticket.title.toLowerCase().includes(searchTerm)) ||
            (ticket.subject && ticket.subject.toLowerCase().includes(searchTerm)) ||
            (ticket.category && ticket.category.toLowerCase().includes(searchTerm)) ||
            (ticket.priority && ticket.priority.toLowerCase().includes(searchTerm)) ||
            (ticket.status && ticket.status.toLowerCase().includes(searchTerm)) ||
            (ticket.assignedTo && ticket.assignedTo.toLowerCase().includes(searchTerm));
    }).filter(t => t.status !== 'Closed');

    displayTickets(filtered);
}

// Show raise ticket modal
function showRaiseTicketModal() {
    const modal = new bootstrap.Modal(document.getElementById('raiseTicketModal'));
    modal.show();
}

// Handle raise ticket form submission
async function handleRaiseTicket(e) {
    e.preventDefault();

    // Check for Demo Mode
    if (document.body.classList.contains('demo-mode')) {
        // Close the form modal first
        const formModal = bootstrap.Modal.getInstance(document.getElementById('raiseTicketModal'));
        if (formModal) formModal.hide();

        // Show Restricted Modal
        const restrictedModal = new bootstrap.Modal(document.getElementById('restrictedActionModal'));
        restrictedModal.show();
        return;
    }

    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Submitting...';

    const subject = document.getElementById('ticketSubject').value;
    const category = document.getElementById('ticketCategory').value;
    const priority = document.getElementById('ticketPriority').value;
    const description = document.getElementById('ticketDescription').value;

    try {
        const token = getAuthToken();
        const response = await fetch('/api/v1/tickets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                title: subject,
                category: category,
                priority: priority,
                description: description
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Close modal and reset form
            const modal = bootstrap.Modal.getInstance(document.getElementById('raiseTicketModal'));
            modal.hide();
            document.getElementById('raiseTicketForm').reset();

            // Reload tickets
            await loadTickets();

            // Show success message
            alert('Ticket created successfully!');
        } else {
            if (Array.isArray(data.error)) {
                const errorMsg = data.error.map(err => `${err.loc.join('.')}: ${err.msg}`).join('\n');
                alert('Validation Error:\n' + errorMsg);
            } else {
                alert(data.error || 'Failed to create ticket');
            }
        }

    } catch (error) {
        console.error('Error creating ticket:', error);
        alert('An error occurred while creating the ticket');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
    }
}

// Toggle sidebar on mobile
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
}

// Calculate time ago
function timeAgo(dateString) {
    if (!dateString) return 'Unknown';
    if (!dateString.endsWith('Z') && !dateString.includes('+')) dateString += 'Z';

    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    let interval = Math.floor(seconds / 31536000);
    if (interval >= 1) {
        return interval + " year" + (interval === 1 ? "" : "s") + " ago";
    }
    interval = Math.floor(seconds / 2592000);
    if (interval >= 1) {
        return interval + " month" + (interval === 1 ? "" : "s") + " ago";
    }
    interval = Math.floor(seconds / 86400);
    if (interval >= 1) {
        return interval + " day" + (interval === 1 ? "" : "s") + " ago";
    }
    interval = Math.floor(seconds / 3600);
    if (interval >= 1) {
        return interval + " hr" + (interval === 1 ? "" : "s") + " ago";
    }
    interval = Math.floor(seconds / 60);
    if (interval >= 1) {
        return interval + " min" + (interval === 1 ? "" : "s") + " ago";
    }
    return Math.floor(seconds) + " seconds ago";
}

// Helper: Format Date
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric'
    });
}

// Helper: Format Time
function formatTime(dateString) {
    if (!dateString) return '';
    return new Date(dateString).toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit'
    });
}

// View ticket details
async function viewTicket(ticketId) {
    // Try to find in cache first
    let ticket = cachedTickets.find(t => t.id == ticketId);

    // If not in cache or we want full details (timeline etc might not be in list view), fetch it
    // But list view usually has enough? Protocol says /ticket/<id> endpoint has comments/timeline. 
    // The list endpoint might not have them.
    // So let's fetch individual ticket to be safe and get Timeline.

    try {
        const token = getAuthToken();
        const response = await fetch(`/api/v1/tickets/${ticketId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            ticket = await response.json();
        }
    } catch (e) {
        console.error("Failed to fetch ticket details", e);
    }

    if (!ticket) {
        alert('Ticket not found');
        return;
    }

    const modalBody = document.getElementById('viewTicketBody');
    document.getElementById('viewTicketTitle').textContent = `Ticket ${formatTicketId(ticket.id)}`;

    modalBody.innerHTML = `
        <div class="row">
            <div class="col-md-6 mb-3">
                <strong>Subject:</strong>
                <p>${ticket.title || ticket.subject}</p>
            </div>
            <div class="col-md-6 mb-3">
                <strong>Category:</strong>
                <p><span class="badge bg-secondary">${ticket.category}</span></p>
            </div>
        </div>
        <div class="row">
            <div class="col-md-6 mb-3">
                <strong>Priority:</strong>
                <p><span class="priority-badge priority-${ticket.priority.toLowerCase()}">${ticket.priority}</span></p>
            </div>
            <div class="col-md-6 mb-3">
                <strong>Status:</strong>
                <p><span class="status-badge status-${ticket.status.toLowerCase().replace(' ', '-')}">${ticket.status}</span></p>
            </div>
        </div>
        <div class="row">
            <div class="col-md-6 mb-3">
                <strong>Assigned To:</strong>
                <p>${ticket.assignedTo || 'Unassigned'}</p>
            </div>
            <div class="col-md-6 mb-3">
                <strong>Created:</strong>
                <p>${formatDate(ticket.createdAt)} at ${formatTime(ticket.createdAt)}</p>
            </div>
        </div>
        <div class="mb-3">
            <strong>Description:</strong>
            <p style="white-space: pre-wrap;">${ticket.description}</p>
        </div>
        <div class="mb-3">
            <strong>Timeline:</strong>
            <div class="timeline mt-3">
                ${ticket.timeline ? ticket.timeline.map(event => `
                    <div class="timeline-item mb-3 p-3" style="background: var(--surface-elevated); border-left: 3px solid var(--primary-500); border-radius: var(--radius-md);">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <strong>${event.action}</strong>
                                <p class="mb-0 text-muted small">by ${event.by}</p>
                                ${event.note ? `<p class="mb-0 mt-1 small">${event.note}</p>` : ''}
                            </div>
                            <small class="text-muted">${timeAgo(event.timestamp)}</small>
                        </div>
                    </div>
                `).join('') : '<p class="text-muted">No history available</p>'}
            </div>
        </div>
        
         <div class="d-flex justify-content-end mt-4">
             <button class="btn btn-outline-danger" onclick="downloadTicketPDF('${ticket.id}')">
                <i class="fas fa-file-pdf me-2"></i>Download PDF
            </button>
        </div>
    `;

    const modal = new bootstrap.Modal(document.getElementById('viewTicketModal'));
    modal.show();
}

// Download ticket as PDF
async function downloadTicketPDF(ticketId) {
    const token = getAuthToken();
    try {
        const response = await fetch(`/api/v1/tickets/${ticketId}/pdf`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Ticket-T-${1000 + parseInt(ticketId)}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();

            // Show success notification
            // Use a simple timeout to ensure the download started
            showToast(`PDF for Ticket T-${1000 + parseInt(ticketId)} has been downloaded.`, 'success');

        } else {
            showToast('Failed to download PDF. Please try again.', 'error');
        }
    } catch (e) {
        console.error("PDF Download failed", e);
        showToast('An error occurred while downloading the PDF.', 'error');
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