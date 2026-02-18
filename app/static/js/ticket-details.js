/* ==========================================================================
   Ticket Details Page - Complete Implementation
   Real-time updates, Comments, Timeline, Activity Log
   ========================================================================== */

// Get ticket ID from URL path (e.g. /ticket/123)
const pathParts = window.location.pathname.split('/');
window.ticketId = pathParts[pathParts.length - 1]; // Last part of the path
const ticketId = window.ticketId; // Local alias for compatibility

// Auto-refresh interval (5 seconds)
let refreshInterval;

// Current user
const currentUser = getCurrentUser();

// State for comments pagination
let showingAllComments = false;

// Check authentication
if (!requireAuth()) {
    // Will redirect if not authenticated
}

// Initialize page
document.addEventListener('DOMContentLoaded', function () {
    if (!ticketId) {
        alert('No ticket ID provided');
        goBack();
        return;
    }

    loadTicketDetails();
    setupEventListeners();
    startAutoRefresh();
});

// Setup event listeners
function setupEventListeners() {
    document.getElementById('commentForm').addEventListener('submit', handleAddComment);
}

// Helper to parse date consistently (assume UTC from server)
function parseDate(dateString) {
    if (!dateString) return new Date();
    // Ensure it's treated as UTC if no timezone specified
    if (!dateString.endsWith('Z') && !dateString.includes('+')) {
        return new Date(dateString + 'Z');
    }
    return new Date(dateString);
}

// Load ticket details
async function loadTicketDetails() {
    try {
        const token = getAuthToken();
        const response = await fetch(`/api/v1/tickets/${ticketId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            if (response.status === 404) {
                alert('Ticket not found');
            } else {
                console.error('Failed to load ticket details');
            }
            if (response.status === 401) return; // Auth redirect handles this
            // Don't goback immediately on transient error
            return;
        }

        const ticket = await response.json();

        // Populate header
        document.getElementById('ticketTitle').textContent = ticket.title;
        // Check if element exists before setting
        const tidEl = document.getElementById('ticketId');
        if (tidEl) tidEl.textContent = `T-${1000 + ticket.id}`;

        // Status badge
        const statusEl = document.getElementById('ticketStatus');
        if (statusEl) statusEl.innerHTML = `<span class="status-badge status-${ticket.status.toLowerCase().replace(' ', '-')}">${ticket.status}</span>`;

        // Priority badge
        const priorityEl = document.getElementById('ticketPriority');
        if (priorityEl) priorityEl.innerHTML = `<span class="priority-badge priority-${ticket.priority.toLowerCase()}">${ticket.priority}</span>`;

        // Category
        const catEl = document.getElementById('ticketCategory');
        if (catEl) catEl.innerHTML = `<span class="badge bg-secondary">${ticket.category}</span>`;

        // PDF Button is already in HTML, checking availability or state if needed can go here.


        // Populate details
        document.getElementById('detailSubject').textContent = ticket.title;
        document.getElementById('detailDescription').textContent = ticket.description;
        document.getElementById('detailCreatedBy').textContent = ticket.createdByName || 'Unknown';
        document.getElementById('detailAssignedTo').textContent = ticket.assignedTo || 'Unassigned';
        document.getElementById('detailCreatedDate').textContent = formatFullDate(ticket.createdAt);
        document.getElementById('detailUpdatedDate').textContent = formatFullDate(ticket.updatedAt || ticket.createdAt);

        // Calculate and display stats
        updateStats(ticket);

        // Render timeline
        renderTimeline(ticket);

        // Render comments
        renderComments(ticket);

        // Initialize Withdraw Button visibility
        const withdrawBtn = document.getElementById('withdrawBtn');
        if (withdrawBtn) {
            // Show only if Status is Open AND Current User is the Creator
            if (ticket.status === 'Open' && currentUser && ticket.createdById === currentUser.id) {
                withdrawBtn.classList.remove('d-none');
            } else {
                withdrawBtn.classList.add('d-none');
            }
        }

    } catch (error) {
        console.error('Error loading ticket:', error);
    }
}

// Withdraw Ticket
async function withdrawTicket() {
    // Check for Demo Mode
    if (document.body.classList.contains('demo-mode')) {
        const restrictedModal = new bootstrap.Modal(document.getElementById('restrictedActionModal'));
        restrictedModal.show();
        return;
    }

    if (!confirm('Are you sure you want to withdraw this ticket? This action cannot be undone.')) {
        return;
    }

    const btn = document.getElementById('withdrawBtn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';

    try {
        const token = getAuthToken();
        const response = await fetch(`/api/v1/tickets/${ticketId}/withdraw`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();

        if (response.ok) {
            showToast('Ticket withdrawn successfully', 'success');
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showToast(data.error || 'Failed to withdraw ticket', 'error');
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    } catch (e) {
        console.error("Withdraw failed", e);
        showToast('An error occurred', 'error');
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Update stats
function updateStats(ticket) {
    // Calculate ticket age
    const createdDate = parseDate(ticket.createdAt);
    const now = new Date();

    // Difference in milliseconds
    const diffMs = now - createdDate;

    // Convert to hours
    const ageInHours = Math.floor(diffMs / (1000 * 60 * 60));
    const ageInDays = Math.floor(ageInHours / 24);

    let ageText;
    if (ageInDays > 0) {
        ageText = `${ageInDays} day${ageInDays !== 1 ? 's' : ''}`;
    } else {
        ageText = `${Math.max(0, ageInHours)} hour${ageInHours !== 1 ? 's' : ''}`;
    }

    document.getElementById('ticketAge').textContent = ageText;

    // Comment count
    const commentCount = (ticket.comments || []).length;
    document.getElementById('commentCount').textContent = commentCount;

    // Update count (timeline events)
    const updateCount = (ticket.timeline || []).length;
    document.getElementById('updateCount').textContent = updateCount;

    // SLA Status
    const slaHours = {
        'Critical': 4,
        'High': 8,
        'Medium': 24,
        'Low': 48
    };

    const maxHours = slaHours[ticket.priority] || 24;
    const slaBreached = ageInHours > maxHours && ticket.status !== 'Resolved' && ticket.status !== 'Closed';

    let slaHtml;
    if (ticket.status === 'Resolved' || ticket.status === 'Closed') {
        slaHtml = '<span class="sla-indicator success"><i class="fas fa-check-circle"></i> Completed</span>';
    } else if (slaBreached) {
        slaHtml = '<span class="sla-indicator danger"><i class="fas fa-exclamation-triangle"></i> Breached</span>';
    } else if (ageInHours > maxHours * 0.8) {
        slaHtml = '<span class="sla-indicator warning"><i class="fas fa-clock"></i> Approaching</span>';
    } else {
        slaHtml = '<span class="sla-indicator success"><i class="fas fa-check"></i> On Track</span>';
    }

    document.getElementById('slaStatus').innerHTML = slaHtml;
}

// Render timeline
function renderTimeline(ticket) {
    const container = document.getElementById('timelineContainer');
    const timeline = ticket.timeline || [];

    if (timeline.length === 0) {
        container.innerHTML = '<p class="text-muted">No activity yet</p>';
        return;
    }

    // Sort timeline by timestamp (newest first)
    const sortedTimeline = [...timeline].sort((a, b) =>
        parseDate(b.timestamp) - parseDate(a.timestamp)
    );

    container.innerHTML = `
        <div class="timeline-line"></div>
        ${sortedTimeline.map((event, index) => {
        const eventType = getEventType(event.action);
        return `
                <div class="timeline-event ${eventType}">
                    <div class="timeline-dot"></div>
                    <div class="timeline-content">
                        <div class="timeline-header">
                            <div>
                                <div class="timeline-action">${event.action}</div>
                                <div class="timeline-user">by ${event.by}</div>
                            </div>
                            <div class="timeline-time">
                                ${formatFullDate(event.timestamp)}
                            </div>
                        </div>
                        ${event.note ? `<div class="timeline-description">${event.note}</div>` : ''}
                    </div>
                </div>
            `;
    }).join('')}
    `;
}

// Get event type for styling
function getEventType(action) {
    if (action.includes('created') || action.includes('Created')) return 'created';
    if (action.includes('Resolved') || action.includes('resolved')) return 'resolved';
    if (action.includes('comment') || action.includes('Comment')) return 'commented';
    return 'updated';
}

// Render comments
function renderComments(ticket) {
    const container = document.getElementById('commentsList');
    const comments = ticket.comments || [];

    if (comments.length === 0) {
        container.innerHTML = '<p class="text-muted">No comments yet. Be the first to comment!</p>';
        return;
    }

    // Organize comments into hierarchy
    const commentMap = {};
    const rootComments = [];

    comments.forEach(comment => {
        comment.children = [];
        commentMap[comment.id] = comment;
    });

    comments.forEach(comment => {
        if (comment.parentId) {
            if (commentMap[comment.parentId]) {
                commentMap[comment.parentId].children.push(comment);
            }
        } else {
            rootComments.push(comment);
        }
    });

    // Sort root comments (newest first)
    rootComments.sort((a, b) => parseDate(b.timestamp) - parseDate(a.timestamp));

    // Pagination logic
    const initialLimit = 3;
    const totalRoots = rootComments.length;

    window.allRootComments = rootComments; // Store for toggling

    function renderList(limit) {
        const visibleComments = limit ? rootComments.slice(0, limit) : rootComments;

        let html = visibleComments.map(comment => renderCommentItem(comment)).join('');

        // Show More Button
        if (totalRoots > initialLimit) {
            if (limit && limit < totalRoots) {
                html += `
                    <div class="text-center mt-3">
                        <button onclick="toggleComments(true)" class="btn btn-sm btn-outline-primary show-more-comments">
                            View All Comments (${totalRoots})
                        </button>
                    </div>
                `;
            } else {
                html += `
                    <div class="text-center mt-3">
                        <button onclick="toggleComments(false)" class="btn btn-sm btn-outline-secondary show-more-comments">
                            Show Less
                        </button>
                    </div>
                `;
            }
        }

        container.innerHTML = html;
    }

    // Initial render based on persisted state
    renderList(showingAllComments ? null : initialLimit);

    // Global toggle function
    window.toggleComments = function (showAll) {
        showingAllComments = showAll;
        renderList(showAll ? null : initialLimit);
    };
}

// Recursive render single comment item
function renderCommentItem(comment) {
    // Sort children (oldest first for conversation flow, or newest? Usually oldest first in replies)
    // Let's go with oldest first for replies to read like a thread
    if (comment.children) {
        comment.children.sort((a, b) => parseDate(a.timestamp) - parseDate(b.timestamp));
    }

    const nameParts = (comment.author || 'U').split(' ');
    const initials = nameParts.length > 1
        ? (nameParts[0][0] + nameParts[nameParts.length - 1][0]).toUpperCase()
        : nameParts[0][0].toUpperCase();

    let html = `
        <div class="comment-item" id="comment-${comment.id}">
            <div class="comment-header">
                <div class="comment-author">
                    <div class="comment-avatar">${initials}</div>
                    <div>
                        <div class="comment-author-name">${comment.author}</div>
                        <div class="comment-time">${timeAgo(comment.timestamp)}</div>
                    </div>
                </div>
                <button onclick="showReplyForm(${comment.id})" class="btn btn-sm btn-link reply-btn">
                    <i class="fas fa-reply"></i> Reply
                </button>
            </div>
            <div class="comment-body">${comment.text}</div>
            
            <!-- Reply Form Container -->
            <div id="reply-form-${comment.id}" class="reply-form-container" style="display: none;"></div>
    `;

    // Render children
    if (comment.children && comment.children.length > 0) {
        html += `<div class="comment-replies">`;
        comment.children.forEach(child => {
            html += renderCommentItem(child);
        });
        html += `</div>`;
    }

    html += `</div>`;
    return html;
}

// Show Reply Form
window.showReplyForm = function (commentId) {
    // Close other reply forms? Optional. For now let's allow multiples.
    const container = document.getElementById(`reply-form-${commentId}`);
    if (container.style.display === 'block') {
        container.style.display = 'none';
        return;
    }

    container.innerHTML = `
        <div class="reply-form mt-2 p-2 border rounded bg-light">
            <textarea id="reply-text-${commentId}" class="form-control mb-2" rows="2" placeholder="Write a reply..."></textarea>
            <div class="d-flex justify-content-end gap-2">
                <button onclick="document.getElementById('reply-form-${commentId}').style.display='none'" class="btn btn-sm btn-outline-secondary">Cancel</button>
                <button onclick="submitReply(${commentId})" class="btn btn-sm btn-primary">Reply</button>
            </div>
        </div>
    `;
    container.style.display = 'block';

    // Focus textarea
    setTimeout(() => document.getElementById(`reply-text-${commentId}`).focus(), 100);
}

// Submit Reply
window.submitReply = async function (parentId) {
    // Check for Demo Mode
    if (document.body.classList.contains('demo-mode')) {
        const restrictedModal = new bootstrap.Modal(document.getElementById('restrictedActionModal'));
        restrictedModal.show();
        return;
    }

    const text = document.getElementById(`reply-text-${parentId}`).value.trim();
    if (!text) return;

    // Show loading?

    try {
        const token = getAuthToken();
        const response = await fetch(`/api/v1/tickets/${ticketId}/comments`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                parent_id: parentId
            })
        });

        if (response.ok) {
            await loadTicketDetails(); // Reload to show new comment
            showSyncStatus('Reply posted', 'success');
        } else {
            alert('Failed to post reply');
        }
    } catch (e) {
        console.error("Failed to post reply", e);
        alert('Error posting reply');
    }
}

// Render recent activity
function renderRecentActivity(ticket) {
    const container = document.getElementById('recentActivity');
    const timeline = ticket.timeline || [];

    // Get last 5 activities
    const recent = [...timeline]
        .sort((a, b) => parseDate(b.timestamp) - parseDate(a.timestamp))
        .slice(0, 5);

    if (recent.length === 0) {
        container.innerHTML = '<p class="text-muted small">No recent activity</p>';
        return;
    }

    container.innerHTML = recent.map(event => `
        <div class="activity-item mb-3 p-2" style="background: var(--surface-elevated); border-radius: var(--radius-md);">
            <div class="small">
                <strong>${event.action}</strong>
                <div class="text-muted">${timeAgo(event.timestamp)}</div>
            </div>
        </div>
    `).join('');
}

// Handle add comment
async function handleAddComment(e) {
    e.preventDefault();

    // Check for Demo Mode
    if (document.body.classList.contains('demo-mode')) {
        const restrictedModal = new bootstrap.Modal(document.getElementById('restrictedActionModal'));
        restrictedModal.show();
        return;
    }

    const commentText = document.getElementById('commentText').value.trim();
    if (!commentText) return;

    // Show button loading state
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Posting...';

    try {
        const token = getAuthToken();
        const response = await fetch(`/api/v1/tickets/${ticketId}/comments`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: commentText })
        });

        if (response.ok) {
            // Clear form
            document.getElementById('commentText').value = '';

            // Reload details immediately
            await loadTicketDetails();

            // Show success feedback
            showSyncStatus('Comment posted', 'success');
        } else {
            alert('Failed to post comment');
        }
    } catch (e) {
        console.error("Failed to post comment", e);
        alert('Error posting comment');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

// Start auto-refresh
function startAutoRefresh() {
    // Refresh every 5 seconds
    refreshInterval = setInterval(() => {
        refreshTicketData();
    }, 5000);
}

// Refresh ticket data
function refreshTicketData() {
    // Check if any reply form is active
    const forms = document.querySelectorAll('.reply-form-container');
    for (let form of forms) {
        if (form.style.display === 'block') {
            // User is replying, skip auto-refresh to prevent losing input
            return;
        }
    }

    showSyncStatus('Syncing...', 'syncing');
    loadTicketDetails();
    // Status update handled in UI helper or after load
    setTimeout(() => {
        showSyncStatus('Updated', 'success');
    }, 500);
}

// Show sync status
function showSyncStatus(message, type) {
    const indicator = document.getElementById('syncStatus');
    if (!indicator) return;

    indicator.className = 'refresh-indicator';
    if (type === 'syncing') {
        indicator.classList.add('syncing');
    }

    indicator.innerHTML = `
        <i class="fas fa-${type === 'syncing' ? 'sync-alt fa-spin' : 'check-circle'}"></i>
        <span>${message}</span>
    `;

    // Reset to default after 2 seconds
    if (type !== 'syncing') {
        setTimeout(() => {
            indicator.innerHTML = `
                <i class="fas fa-sync-alt"></i>
                <span>Auto-updating</span>
            `;
            indicator.className = 'refresh-indicator';
        }, 2000);
    }
}

// Print ticket
function printTicket() {
    window.print();
}

// Go back to dashboard
function goBack() {
    // Stop auto-refresh
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }

    // Use centralized redirect logic from auth.js
    if (typeof redirectToDashboard === 'function') {
        redirectToDashboard();
    } else {
        // Fallback if auth.js not loaded
        window.location.href = '/';
    }
}

// Format full date with time
function formatFullDate(dateString) {
    if (!dateString) return '-';
    const date = parseDate(dateString);
    const dateOptions = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return date.toLocaleDateString('en-US', dateOptions);
}

// Calculate time ago
function timeAgo(dateString) {
    if (!dateString) return 'Unknown';

    // Use parseDate to handle timezone consistently
    const date = parseDate(dateString);
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

// Cleanup on page unload
window.addEventListener('beforeunload', function () {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

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

// Helper: Format Ticket ID
function formatTicketId(id) {
    return `T-${1000 + parseInt(id)}`;
}