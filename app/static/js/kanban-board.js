/* ==========================================================================
   Dedicated Ticket Board (Kanban) JavaScript
   ========================================================================== */

if (!requireAuth()) { }
const user = getCurrentUser();

let cachedTickets = [];
const statusMap = {
    'Open': 'todo',
    'New': 'todo',
    'In Progress': 'inprogress',
    'Resolved': 'done', // Map Resolved and Closed to Done
    'Closed': 'done'
};


document.addEventListener('DOMContentLoaded', async function () {
    initializeSidebar();
    await loadTickets();
    initKanbanBoard();
});

function initializeSidebar() {
    // Set user info
    document.getElementById('userName').textContent = user.full_name || user.name || 'User';
    document.getElementById('userRole').textContent = user.role.replace('_', ' ').toUpperCase();
    
    const initials = (user.full_name || user.name || 'U').split(' ').map(n => n[0]).join('').toUpperCase();
    document.getElementById('userAvatar').textContent = initials;

    // Adjust dashboard link based on role
    const dashboardLink = document.querySelector('#sidebar-dashboard-link a');
    if (user.role === 'admin') {
        dashboardLink.href = '/dashboard/admin';
    } else if (user.role === 'itstaff' || user.role === 'it_staff') {
        dashboardLink.href = '/dashboard/it-staff';
    } else {
        dashboardLink.href = '/dashboard/employee';
    }
}

async function loadTickets() {
    const token = getAuthToken();
    try {
        const response = await fetch('/api/v1/tickets', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            cachedTickets = await response.json();
            renderKanbanBoard();
        }
    } catch (e) {
        console.error("Failed to fetch tickets", e);
    }
}

function renderKanbanBoard() {
    const lists = {
        todo: document.getElementById('kanban-list-todo'),
        inprogress: document.getElementById('kanban-list-inprogress'),
        done: document.getElementById('kanban-list-done')
    };

    // Clear lists
    Object.values(lists).forEach(list => { if (list) list.innerHTML = ''; });

    const counts = { todo: 0, inprogress: 0, done: 0 };

    cachedTickets.forEach(ticket => {
        const colKey = statusMap[ticket.status] || 'todo';
        const list = lists[colKey];
        if (list) {
            const card = createKanbanCard(ticket);
            list.appendChild(card);
            counts[colKey]++;
        }
    });

    // Update badges
    Object.keys(counts).forEach(key => {
        const el = document.getElementById(`kanban-count-${key}`);
        if (el) el.textContent = counts[key];
    });
}

function createKanbanCard(ticket) {
    const card = document.createElement('div');
    card.className = 'kanban-card';
    card.dataset.id = ticket.id;
    card.dataset.status = ticket.status;

    const initials = (ticket.createdByName || ticket.createdBy || 'U').split(' ').map(n => n[0]).join('').toUpperCase();
    const priority = ticket.priority || 'Medium';
    const createdAt = timeAgo(ticket.createdAt);

    card.innerHTML = `
        <div class="kanban-card-header">
            <span class="kanban-ticket-id">#${ticket.id}</span>
            <div class="priority-indicator">
                <span class="priority-dot priority-${priority.toLowerCase()}-dot"></span>
                <span class="priority-badge priority-${priority.toLowerCase()}">${priority}</span>
            </div>
        </div>
        <div class="kanban-card-title">${ticket.subject || ticket.title}</div>
        <div class="kanban-card-tags">
            <span class="kanban-tag">${ticket.category}</span>
        </div>
        <div class="kanban-card-footer">
            <div class="kanban-assignee">
                <div class="kanban-avatar" title="Created by ${ticket.createdByName || ticket.createdBy}">${initials}</div>
                <span class="kanban-due-date"><i class="far fa-clock"></i> ${createdAt}</span>
            </div>
        </div>
    `;

    card.onclick = () => window.location.href = `/ticket/${ticket.id}`;
    return card;
}

function initKanbanBoard() {
    const isReadOnly = user.role === 'admin' || user.role === 'employee';

    if (isReadOnly) {
        const boardContainer = document.querySelector('.kanban-board-container');
        if (boardContainer) {
            boardContainer.classList.add('read-only-board');
        }
    }

    const columns = ['kanban-list-todo', 'kanban-list-inprogress', 'kanban-list-done'];
    columns.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            new Sortable(el, {
                group: 'tickets',
                animation: 200,
                ghostClass: 'sortable-ghost',
                disabled: isReadOnly,
                onEnd: handleKanbanDrop
            });
        }
    });
}

async function handleKanbanDrop(evt) {
    const itemEl = evt.item;
    const ticketId = itemEl.dataset.id;
    const oldStatus = itemEl.dataset.status;
    const newColumnParams = evt.to.closest('.kanban-column');
    const newStatus = newColumnParams ? newColumnParams.dataset.status : null;

    if (!newStatus || oldStatus === newStatus) return;

    // Basic role-based restrictions
    if (user.role === 'employee' && newStatus !== 'Withdrawn') {
        showKanbanError("Employees can only view the board or withdraw tickets.");
        loadTickets(); // Revert
        return;
    }

    // Prevent moving from In Progress to Open
    if (oldStatus === 'In Progress' && newStatus === 'Open') {
        showKanbanError("Invalid move: Cannot move a ticket from In Progress back to To Do.");
        loadTickets(); // Revert
        return;
    }

    try {
        const token = getAuthToken();
        const response = await fetch(`/api/v1/tickets/${ticketId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ status: newStatus })
        });

        if (response.ok) {
            itemEl.dataset.status = newStatus;
            
            // Add pulse animation to the target counter
            const newColKey = statusMap[newStatus];
            const badgeEl = document.getElementById(`kanban-count-${newColKey}`);
            if (badgeEl) {
                badgeEl.classList.add('pulse-animation');
                setTimeout(() => badgeEl.classList.remove('pulse-animation'), 500);
            }

            // Await loadTickets so it blocks and renders the counts immediately
            await loadTickets();
        } else {
            const data = await response.json();
            showKanbanError(data.error || "Failed to update ticket status.");
            await loadTickets();
        }
    } catch (e) {
        console.error(e);
        showKanbanError("An error occurred while updating the ticket.");
        await loadTickets();
    }
}

function showKanbanError(msg) {
    const errorEl = document.getElementById('kanbanErrorMessage');
    if (errorEl) errorEl.textContent = msg;
    const modal = new bootstrap.Modal(document.getElementById('kanbanErrorModal'));
    modal.show();
}

/**
 * Helper: Time Ago
 */
function timeAgo(date) {
    if (!date) return 'Unknown';
    const seconds = Math.floor((new Date() - new Date(date)) / 1000);
    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + "y ago";
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + "mo ago";
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + "d ago";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + "h ago";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + "m ago";
    return "just now";
}
