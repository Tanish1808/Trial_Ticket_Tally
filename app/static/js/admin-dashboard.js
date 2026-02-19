/* ==========================================================================
   Admin Dashboard JavaScript
   Full System Management with Charts and Analytics
   ========================================================================== */

// Authentication check
if (!requireAuth()) {
    // Will redirect if not authenticated
}

const user = getCurrentUser();
if (!user || user.role !== 'admin') {
    alert('Access denied. Administrator privileges required.');
    redirectToDashboard();
}

// Chart instances
let lineChart, pieChart, barChart;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function () {
    initializeDashboard();
    loadDashboardData();
    setupEventListeners();
    initializeCharts();
    showSection('dashboard');

    showSection('dashboard');

    // Auto Refresh Logic
    const autoRefresh = localStorage.getItem('auto-refresh') !== 'false'; // Default true
    if (autoRefresh) {
        setInterval(() => {
            // Only refresh if tab is visible
            if (!document.hidden) {
                if (document.getElementById('dashboardSection').style.display === 'block') {
                    loadDashboardData();
                } else if (document.getElementById('ticketsSection').style.display === 'block') {
                    loadAllTickets(currentTicketFilter);
                }
            }
        }, 30000); // 30 seconds
    }
});

// Initialize dashboard
function initializeDashboard() {
    document.getElementById('userName').textContent = user.name || 'Administrator';
    document.getElementById('welcomeMessage').textContent = `Welcome Back, ${user.name || 'Admin'}!`;

    // Set user avatar initials
    const initials = (user.name || 'AD').split(' ').map(n => n[0]).join('').toUpperCase();
    document.getElementById('userAvatar').textContent = initials;

    // Set current date
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('currentDate').textContent = new Date().toLocaleDateString('en-US', options);

    // Load fresh profile data
    loadProfile();
}

// Load User Profile
async function loadProfile() {
    try {
        const response = await fetch('/api/v1/users/me', {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (response.ok) {
            const userData = await response.json();

            // Update Sidebar & Header (in case name changed)
            document.getElementById('userName').textContent = userData.full_name;
            document.getElementById('welcomeMessage').textContent = `Welcome Back, ${userData.full_name}!`;
            const initials = userData.full_name.split(' ').map(n => n[0]).join('').toUpperCase();
            document.getElementById('userAvatar').textContent = initials;

            // Update Profile Section
            const profileAvatar = document.getElementById('profileAvatar');
            if (profileAvatar) profileAvatar.textContent = initials;

            const els = {
                'profileName': userData.full_name,
                'profileRole': userData.role ? (userData.role.charAt(0).toUpperCase() + userData.role.slice(1)) : 'User',
                'profileEmail': userData.email,
                'profileDepartment': userData.department || 'Not Assigned',
                'profileJoined': userData.created_at ? new Date(userData.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : 'N/A',
                'profileId': `#${userData.id}`
            };

            for (const [id, value] of Object.entries(els)) {
                const el = document.getElementById(id);
                if (el) el.textContent = value;
            }
        }
    } catch (e) {
        console.error("Failed to load profile", e);
    }
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('addStaffForm').addEventListener('submit', handleAddStaff);
    document.getElementById('changePriorityForm').addEventListener('submit', handleChangePriority);

    const searchInput = document.getElementById('searchAllTickets');
    if (searchInput) {
        searchInput.addEventListener('input', handleSearch);
    }
}

// Ticket Cache
let allTicketsCache = [];

function getTickets() {
    return allTicketsCache;
}

// Get tickets from API
async function fetchTickets() {
    try {
        const response = await fetch('/api/v1/tickets', {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });
        if (response.ok) {
            allTicketsCache = await response.json();
            return allTicketsCache;
        }
    } catch (e) {
        console.error("Failed to fetch tickets", e);
    }
    return [];
}

// [REMOVED] localStorage staff logic

// Load dashboard data
async function loadDashboardData() {
    try {
        const response = await fetch('/api/v1/analytics/dashboard', {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (response.ok) {
            const data = await response.json();

            document.getElementById('totalTickets').textContent = data.total_tickets;
            document.getElementById('openTickets').textContent = data.open_tickets;
            document.getElementById('inProgressTickets').textContent = data.in_progress_tickets;
            document.getElementById('resolvedTickets').textContent = data.resolved_today;

            // Re-init charts with real data
            updateCharts(data);
        }
    } catch (e) {
        console.error("Failed to load dashboard stats", e);
    }
}

function updatePerformanceChart(staffData) {
    // [Removed as requested]
}

// Update charts with data
function updateCharts(data) {
    // Line Chart - Ticket Trends
    const lineCtx = document.getElementById('lineChart');
    if (lineCtx && data.trends) {
        if (lineChart) {
            lineChart.data.labels = data.trends.dates;
            lineChart.data.datasets[0].data = data.trends.created;
            lineChart.data.datasets[1].data = data.trends.resolved;
            lineChart.update('none');
        } else {
            lineChart = new Chart(lineCtx.getContext('2d'), {
                type: 'line',
                data: {
                    labels: data.trends.dates,
                    datasets: [
                        {
                            label: 'Created',
                            data: data.trends.created,
                            borderColor: 'rgb(37, 99, 235)',
                            backgroundColor: 'rgba(37, 99, 235, 0.1)',
                            tension: 0.4,
                            fill: true,
                            spanGaps: true
                        },
                        {
                            label: 'Resolved',
                            data: data.trends.resolved,
                            borderColor: 'rgb(16, 185, 129)',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            tension: 0.4,
                            fill: true,
                            spanGaps: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false // Disable initial animation too if desired, but 'none' on update covers most lag
                }
            });
        }
    }

    // Pie Chart - Category
    const pieCtx = document.getElementById('pieChart');
    if (pieCtx && data.categories) {
        if (pieChart) {
            pieChart.data.labels = Object.keys(data.categories);
            pieChart.data.datasets[0].data = Object.values(data.categories);
            pieChart.update('none');
        } else {
            pieChart = new Chart(pieCtx.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: Object.keys(data.categories),
                    datasets: [{
                        data: Object.values(data.categories),
                        backgroundColor: ['#3b82f6', '#f59e0b', '#10b981', '#06b6d4', '#8b5cf6']
                    }]
                },
                options: { responsive: true }
            });
        }
    }

    // Bar Chart - Priority
    const barCtx = document.getElementById('barChart');
    if (barCtx && data.priorities) {
        // Enforce fixed order: Low -> Medium -> High -> Critical
        const order = ['Low', 'Medium', 'High', 'Critical'];
        const values = order.map(p => data.priorities[p] || 0);

        if (barChart) {
            barChart.data.labels = order;
            barChart.data.datasets[0].data = values;
            barChart.update('none');
        } else {
            barChart = new Chart(barCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: order,
                    datasets: [{
                        label: 'Tickets',
                        data: values,
                        backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#ef4444']
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }
    }

    // SLA Chart - Compliance


}

// Pagination state
let currentPage = 1;
const itemsPerPage = 10;
let currentFilteredTickets = [];

// Initialize charts (Placeholder)
function initializeCharts() {
    // Do nothing, wait for data
}

// Show section
function showSection(section) {
    // Hide all sections
    const sections = ['dashboardSection', 'ticketsSection', 'usersSection', 'itstaffSection', 'messagesSection'];
    sections.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });

    // Update nav links
    document.querySelectorAll('.nav-link-item').forEach(link => {
        link.classList.remove('active');
    });

    // Highlight active sidebar link
    const activeLinkId = `nav-${section}`;
    const activeLink = document.getElementById(activeLinkId);
    if (activeLink) activeLink.classList.add('active');

    // Show selected section
    if (section === 'dashboard') {
        document.getElementById('dashboardSection').style.display = 'block';
    } else if (section === 'tickets') {
        document.getElementById('ticketsSection').style.display = 'block';
        currentPage = 1;
        loadAllTickets();
    } else if (section === 'users') {
        document.getElementById('usersSection').style.display = 'block';
        loadUsers();
    } else if (section === 'itstaff') {
        document.getElementById('itstaffSection').style.display = 'block';
        loadITStaff();
    } else if (section === 'messages') {
        document.getElementById('messagesSection').style.display = 'block';
        loadMessages();
    }
}

// Current filter state
let currentTicketFilter = 'all';

// Load all tickets with optional filter
async function loadAllTickets(filter = null) {
    if (filter) currentTicketFilter = filter;

    await fetchTickets(); // Refresh cache
    const allTickets = getTickets();
    let tickets = allTickets;

    // For "Closed (7 days)" filter - only show closed tickets from last 7 days
    if (currentTicketFilter === 'Closed') {
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

        tickets = allTickets.filter(t => {
            if (t.status !== 'Closed') return false;
            // Assuming updated_at usage or just check valid dates (simplified)
            return true;
        });
    } else if (currentTicketFilter !== 'all') {
        tickets = allTickets.filter(t => t.status === currentTicketFilter);
    }

    // Helper: Verify "Show Closed" preference
    const showClosed = localStorage.getItem('show-closed') === 'true'; // Default false for "Show Closed" usually
    if (!showClosed && currentTicketFilter !== 'Closed') {
        // Filter out closed tickets from "All" and other non-closed views
        if (currentTicketFilter === 'all') {
            tickets = tickets.filter(t => t.status !== 'Closed');
        }
    }

    // Sort by priority and date
    const priorityOrder = { 'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1 };
    tickets.sort((a, b) => {
        const priorityDiff = priorityOrder[b.priority] - priorityOrder[a.priority];
        if (priorityDiff !== 0) return priorityDiff;
        return new Date(b.createdAt) - new Date(a.createdAt);
    });

    currentFilteredTickets = tickets;
    renderTicketsTable();
}

function renderTicketsTable() {
    const tbody = document.getElementById('allTicketsTableBody');
    const paginationControls = document.getElementById('paginationControls');

    if (currentFilteredTickets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center py-5"><div class="text-muted"><i class="fas fa-inbox fa-3x mb-3"></i><p>No tickets found</p></div></td></tr>';
        if (paginationControls) paginationControls.style.display = 'none';
        return;
    }

    // Pagination Logic
    const totalPages = Math.ceil(currentFilteredTickets.length / itemsPerPage);
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const start = (currentPage - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    const pageItems = currentFilteredTickets.slice(start, end);

    tbody.innerHTML = pageItems.map(ticket => `
        <tr>
            <td><strong>${formatTicketId(ticket.id)}</strong></td>
            <td>${ticket.title}</td>
            <td><span class="badge bg-secondary">${ticket.category || 'General'}</span></td>
            <td><span class="priority-badge priority-${ticket.priority.toLowerCase()}">${ticket.priority}</span></td>
            <td><span class="status-badge status-${ticket.status.toLowerCase().replace(' ', '-')}">${ticket.status}</span></td>
            <td>${ticket.createdByName || 'Unknown'}</td>
            <td>${ticket.assignedTo || '<span class="text-muted">Unassigned</span>'}</td>
            <td>${ticket.createdAt ? timeAgo(ticket.createdAt) : ''}</td>
            <td>
                <div class="d-flex gap-2">
                    <a href="/ticket/${ticket.id}" class="btn btn-sm btn-view" title="View Details">
                        <i class="fas fa-eye"></i>
                    </a>
                    <button class="btn btn-sm btn-primary-custom" onclick="showChangePriorityModal('${ticket.id}')" title="Change Priority">
                        <i class="fas fa-flag"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');

    renderPaginationControls(totalPages);
}

function renderPaginationControls(totalPages) {
    let controls = document.getElementById('paginationControls');
    if (!controls) {
        controls = document.createElement('div');
        controls.id = 'paginationControls';
        document.getElementById('allTicketsTableBody').parentElement.after(controls);
    }

    if (totalPages <= 1) {
        controls.style.display = 'none';
        return;
    }

    controls.style.display = 'flex';
    controls.className = 'pagination-custom-container mt-4';

    const startItem = (currentPage - 1) * itemsPerPage + 1;
    const endItem = Math.min(currentPage * itemsPerPage, currentFilteredTickets.length);

    let paginationHtml = `
        <div class="pagination-info">
            Showing <span class="text-primary-500 fw-bold">${startItem}</span> to <span class="text-primary-500 fw-bold">${endItem}</span> of <span class="fw-bold">${currentFilteredTickets.length}</span> entries
        </div>
        <div class="pagination-pill-group">
            <button class="pagination-pill" onclick="changePage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''} aria-label="Previous">
                <i class="fas fa-chevron-left"></i>
            </button>
    `;

    // Calculate range of page numbers to show
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    if (endPage - startPage < 4) startPage = Math.max(1, endPage - 4);

    for (let i = startPage; i <= endPage; i++) {
        paginationHtml += `
            <button class="pagination-pill ${i === currentPage ? 'active' : ''}" onclick="changePage(${i})">
                ${i}
            </button>
        `;
    }

    paginationHtml += `
            <button class="pagination-pill" onclick="changePage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''} aria-label="Next">
                <i class="fas fa-chevron-right"></i>
            </button>
        </div>
    `;

    controls.innerHTML = paginationHtml;
}

window.changePage = function (page) {
    currentPage = page;
    renderTicketsTable();
    // Scroll to top of table
    document.getElementById('ticketsSection').scrollIntoView({ behavior: 'smooth' });
}

// Filter admin tickets by status
function filterAdminTickets(status) {
    currentTicketFilter = status;
    loadAllTickets(status);

    // Update active tab
    document.querySelectorAll('#ticketStatusTabs .nav-link').forEach(link => {
        link.classList.remove('active');
    });
    event.target.closest('.nav-link').classList.add('active');
}

// Load users (Employees only)
async function loadUsers() {
    try {
        // Fetch only employees
        const response = await fetch('/api/v1/users?role=employee', {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (!response.ok) return;

        const users = await response.json();
        const tbody = document.getElementById('usersTableBody');

        if (users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center py-5"><div class="text-muted"><i class="fas fa-users fa-3x mb-3"></i><p>No employees found</p></div></td></tr>';
            return;
        }

        tbody.innerHTML = users.map(user => `
            <tr>
                <td><strong>${user.full_name}</strong></td>
                <td>${user.email}</td>
                <td><span class="badge bg-secondary">${user.department || 'N/A'}</span></td>
                <td>${user.tickets_raised}</td>
                <td>${user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}</td>
            </tr>
        `).join('');

    } catch (e) {
        console.error("Failed to load users", e);
    }
}

// Load IT staff from API
async function loadITStaff() {
    try {
        const response = await fetch('/api/v1/users?role=it_staff', {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (!response.ok) return;

        const staff = await response.json();
        const tbody = document.getElementById('staffTableBody');

        if (staff.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center py-5"><div class="text-muted"><i class="fas fa-user-cog fa-3x mb-3"></i><p>No IT staff members</p></div></td></tr>';
            return;
        }

        tbody.innerHTML = staff.map((member) => `
            <tr>
                <td><strong>${member.full_name}</strong></td>
                <td>${member.email}</td>
                <td><span class="badge bg-primary">${member.team || 'Unassigned'}</span></td>
                <td class="text-center fw-bold text-success">${member.tickets_resolved || 0}</td>
                <td><span class="status-badge ${member.is_active ? 'status-resolved' : 'status-closed'}">${member.is_active ? 'Active' : 'Inactive'}</span></td>
                <td>
                    <button class="btn btn-sm btn-warning" onclick="toggleStaffStatus('${member.id}', ${member.is_active})" title="${member.is_active ? 'Deactivate' : 'Activate'}">
                        <i class="fas fa-${member.is_active ? 'ban' : 'check'}"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error("Failed to load IT staff", e);
    }
}

// Show add staff modal
function showAddStaffModal() {
    const modal = new bootstrap.Modal(document.getElementById('addStaffModal'));
    modal.show();
}

// Handle add staff
async function handleAddStaff(e) {
    e.preventDefault();

    const name = document.getElementById('staffName').value;
    const email = document.getElementById('staffEmail').value;
    const team = document.getElementById('staffTeam').value;
    const btn = e.target.querySelector('button[type="submit"]');
    const originalText = btn.innerHTML;

    // Prevent Double Click
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Adding...';
    }

    try {
        const response = await fetch('/api/v1/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                full_name: name,
                email: email,
                team: team,
                role: 'it_staff',
                password: 'itstaff@tt' // Default password
            })
        });

        if (response.ok) {
            // Close modal and reset form
            const modal = bootstrap.Modal.getInstance(document.getElementById('addStaffModal'));
            modal.hide();
            document.getElementById('addStaffForm').reset();

            // Reload IT staff table
            loadITStaff();

            // Show Success Toast
            showToast(`IT Staff "${name}" is added`);
        } else {
            const data = await response.json();
            alert(data.error || 'Failed to add staff member');
        }
    } catch (e) {
        console.error("Failed to add staff", e);
        alert('Error adding staff member');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
}

// Show Toast Notification
function showToast(message) {
    const toastEl = document.getElementById('liveToast');
    const toastBody = document.getElementById('toastMessage');
    if (toastEl && toastBody) {
        toastBody.textContent = message;
        // Initialize with options: auto-hide after 3 seconds, animated
        const toast = new bootstrap.Toast(toastEl, {
            animation: true,
            autohide: true,
            delay: 3000
        });
        toast.show();
    }
}

// Toggle staff status
async function toggleStaffStatus(userId, currentStatus) {
    try {
        const response = await fetch(`/api/v1/users/${userId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({ is_active: !currentStatus })
        });

        if (response.ok) {
            loadITStaff();
            alert(`Staff member status updated.`);
        } else {
            alert('Failed to update status');
        }
    } catch (e) {
        console.error("Failed to update status", e);
    }
}

// Load Messages
async function loadMessages() {
    try {
        const response = await fetch('/api/v1/admin/messages', {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (!response.ok) return;

        const messages = await response.json();
        const tbody = document.getElementById('messagesTableBody');

        if (messages.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center py-5"><div class="text-muted"><i class="fas fa-inbox fa-3x mb-3"></i><p>No messages found</p></div></td></tr>';
            return;
        }

        tbody.innerHTML = messages.map(msg => `
            <tr class="${msg.is_read ? '' : 'fw-bold'}" style="${msg.is_read ? '' : 'background-color: var(--surface-elevated)'}">
                <td>
                    <div>${msg.name}</div>
                    <small class="text-muted">${msg.email}</small>
                </td>
                <td>
                    <div>${msg.subject}</div>
                    <small class="text-muted text-truncate d-block" style="max-width: 300px;">${msg.message}</small>
                </td>
                <td>${new Date(msg.created_at).toLocaleDateString()}</td>
                <td>
                    <span class="badge ${msg.is_read ? 'bg-secondary' : 'bg-success'}">
                        ${msg.is_read ? 'Read' : 'New'}
                    </span>
                </td>
                <td>
                    ${!msg.is_read ? `
                    <button class="btn btn-sm btn-outline-primary" onclick="markAsRead(${msg.id})" title="Mark as Read">
                        <i class="fas fa-check"></i>
                    </button>` : '<span class="text-muted"><i class="fas fa-check-double"></i></span>'}
                </td>
            </tr>
        `).join('');

    } catch (e) {
        console.error("Failed to load messages", e);
    }
}

// Mark Message as Read
async function markAsRead(id) {
    try {
        const response = await fetch(`/api/v1/admin/messages/${id}/read`, {
            method: 'PATCH',
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (response.ok) {
            loadMessages(); // Reload table
            showToast("Message marked as read");
        }
    } catch (e) {
        console.error("Failed to mark message", e);
    }
}

// Show change priority modal
function showChangePriorityModal(ticketId) {
    const tickets = getTickets();
    // Use loose equality as ticketId is string from HTML and t.id is number from API
    const ticket = tickets.find(t => t.id == ticketId);

    if (!ticket) return;

    // Check if ticket status restricts changes
    const restrictedStatuses = ['Resolved', 'Closed', 'Withdrawn'];
    if (restrictedStatuses.includes(ticket.status)) {
        document.getElementById('statusInfoMessage').textContent = `This ticket is ${ticket.status}. Priority cannot be changed.`;
        const infoEl = document.getElementById('statusInfoModal');
        const infoModal = bootstrap.Modal.getInstance(infoEl) || new bootstrap.Modal(infoEl);
        infoModal.show();
        return;
    }

    document.getElementById('priorityTicketId').value = ticketId;
    document.getElementById('priorityModalTitle').textContent = `Change Priority - ${formatTicketId(ticketId)}`;
    document.getElementById('newPriority').value = ticket.priority;

    const el = document.getElementById('changePriorityModal');
    const modal = bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el);
    modal.show();
}

// Handle change priority
async function handleChangePriority(e) {
    e.preventDefault();

    const ticketId = document.getElementById('priorityTicketId').value;
    const newPriority = document.getElementById('newPriority').value;

    try {
        const response = await fetch(`/api/v1/tickets/${ticketId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({ priority: newPriority })
        });

        if (response.ok) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('changePriorityModal'));
            modal.hide();

            // Reload tickets
            loadAllTickets();
            loadDashboardData();

            alert(`Ticket ${ticketId} priority changed to ${newPriority}`);
        } else {
            alert('Failed to update priority');
        }
    } catch (e) {
        console.error("Failed to update priority", e);
        alert('Error updating priority');
    }
}

// Format Ticket ID
function formatTicketId(id) {
    return `T-${1000 + parseInt(id)}`;
}

// Handle search
function handleSearch(e) {
    const searchTerm = e.target.value.toLowerCase();
    const allTickets = getTickets();

    // Apply current filter first
    let tickets = allTickets;
    if (currentTicketFilter !== 'all') {
        if (currentTicketFilter === 'Closed') {
            const sevenDaysAgo = new Date();
            sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
            tickets = allTickets.filter(t => {
                if (t.status !== 'Closed') return false;
                if (!t.closedAt) return true;
                const closedDate = new Date(t.closedAt);
                return closedDate >= sevenDaysAgo;
            });
        } else {
            tickets = allTickets.filter(t => t.status === currentTicketFilter);
        }
    }

    // Apply search filter
    const filtered = tickets.filter(ticket =>
        formatTicketId(ticket.id).toLowerCase().includes(searchTerm) ||
        String(ticket.id).includes(searchTerm) ||
        ticket.title.toLowerCase().includes(searchTerm) ||
        (ticket.category && ticket.category.toLowerCase().includes(searchTerm)) ||
        (ticket.priority && ticket.priority.toLowerCase().includes(searchTerm)) ||
        ticket.status.toLowerCase().includes(searchTerm) ||
        (ticket.createdByName && ticket.createdByName.toLowerCase().includes(searchTerm))
    );

    // Sort by priority
    const priorityOrder = { 'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1 };
    filtered.sort((a, b) => {
        const priorityDiff = priorityOrder[b.priority] - priorityOrder[a.priority];
        if (priorityDiff !== 0) return priorityDiff;
        return new Date(b.createdAt) - new Date(a.createdAt);
    });

    currentFilteredTickets = filtered;
    currentPage = 1; // Reset to page 1 on search
    renderTicketsTable();
}

// Toggle sidebar on mobile
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
}