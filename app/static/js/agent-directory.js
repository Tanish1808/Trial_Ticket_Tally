/* ==========================================================================
   Agent Directory JavaScript
   ========================================================================== */

if (!requireAuth()) {
    // Redirects if not logged in
}

const currentUser = getCurrentUser();
let cachedAgents = [];

document.addEventListener('DOMContentLoaded', function () {
    if (!currentUser) {
        alert('Session expired. Please login again.');
        window.location.href = '/login';
        return;
    }

    setupTheme();
    renderSidebar();
    loadDirectoryFilters();
    loadAgents();
    setupEventListeners();
});

// Setup Dark/Light Theme on Load
function setupTheme() {
    const currentTheme = localStorage.getItem('ticket-tally-theme') || 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
        const icon = darkModeToggle.querySelector('i');
        if (icon) {
            icon.className = currentTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
        darkModeToggle.addEventListener('click', function () {
            const nextTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', nextTheme);
            localStorage.setItem('ticket-tally-theme', nextTheme);
            if (icon) {
                icon.className = nextTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
            }
        });
    }
}

// Render appropriate sidebar based on User Role
function renderSidebar() {
    // Set user info in footer
    document.getElementById('userName').textContent = currentUser.name || "User";
    const initials = (currentUser.name || "U").split(' ').map(n => n[0]).join('').toUpperCase();
    document.getElementById('userAvatar').textContent = initials;

    let roleDisplay = 'Employee';
    const role = currentUser.role.toLowerCase().replace('_', '');
    if (role === 'itstaff') {
        roleDisplay = 'IT Staff';
    } else if (role === 'admin') {
        roleDisplay = 'Admin';
    }
    document.getElementById('userRole').textContent = roleDisplay;

    // Build sidebar links
    const navLinksContainer = document.getElementById('dynamicNavLinks');
    let html = '';

    if (role === 'employee') {
        html = `
            <li class="nav-item">
                <a href="/dashboard/employee" class="nav-link-item"><i class="fas fa-home"></i><span>Dashboard</span></a>
            </li>
            <li class="nav-item">
                <a href="/ticket-board" class="nav-link-item"><i class="fas fa-columns"></i><span>Ticket Board</span></a>
            </li>
            <li class="nav-item">
                <a href="/calendar" class="nav-link-item"><i class="fas fa-calendar-alt"></i><span>Calendar</span></a>
            </li>
            <li class="nav-item">
                <a href="/agent-directory" class="nav-link-item active"><i class="fas fa-address-book"></i><span>Agent Directory</span></a>
            </li>
        `;
    } else if (role === 'itstaff') {
        html = `
            <li class="nav-item">
                <a href="/dashboard/it-staff" class="nav-link-item"><i class="fas fa-home"></i><span>Dashboard</span></a>
            </li>
            <li class="nav-item">
                <a href="/ticket-board" class="nav-link-item"><i class="fas fa-columns"></i><span>Ticket Board</span></a>
            </li>
            <li class="nav-item">
                <a href="/calendar" class="nav-link-item"><i class="fas fa-calendar-alt"></i><span>Calendar</span></a>
            </li>
            <li class="nav-item">
                <a href="/agent-directory" class="nav-link-item active"><i class="fas fa-address-book"></i><span>Agent Directory</span></a>
            </li>
        `;
    } else if (role === 'admin') {
        html = `
            <li class="nav-item">
                <a href="/dashboard/admin" class="nav-link-item"><i class="fas fa-chart-line"></i><span>Dashboard</span></a>
            </li>
            <li class="nav-item">
                <a href="/ticket-board" class="nav-link-item"><i class="fas fa-columns"></i><span>Ticket Board</span></a>
            </li>
            <li class="nav-item">
                <a href="/projects" class="nav-link-item"><i class="fas fa-project-diagram"></i><span>Projects</span></a>
            </li>
            <li class="nav-item">
                <a href="/calendar" class="nav-link-item"><i class="fas fa-calendar-alt"></i><span>Calendar</span></a>
            </li>
            <li class="nav-item">
                <a href="/agent-directory" class="nav-link-item active"><i class="fas fa-address-book"></i><span>Agent Directory</span></a>
            </li>
        `;
    }

    navLinksContainer.innerHTML = html;
}

// Load specialty and team filters dynamically
async function loadDirectoryFilters() {
    const token = getAuthToken();
    
    // 1. Load Specialties
    try {
        const resSpec = await fetch('/api/v1/users/specialties', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (resSpec.ok) {
            const specialties = await resSpec.json();
            const filterSpecialty = document.getElementById('filterSpecialty');
            specialties.forEach(spec => {
                const opt = document.createElement('option');
                opt.value = spec;
                opt.textContent = spec;
                filterSpecialty.appendChild(opt);
            });
        }
    } catch (e) {
        console.error("Failed to load specialties", e);
    }

    // 2. Load Teams
    try {
        const resTeam = await fetch('/api/v1/users/teams', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (resTeam.ok) {
            const teams = await resTeam.json();
            const filterTeam = document.getElementById('filterTeam');
            teams.forEach(team => {
                const opt = document.createElement('option');
                opt.value = team.id;
                opt.textContent = team.name;
                filterTeam.appendChild(opt);
            });
        }
    } catch (e) {
        console.error("Failed to load teams", e);
    }
}

// Fetch agents from API
async function loadAgents() {
    const grid = document.getElementById('agentGrid');
    grid.innerHTML = '<div class="w-100 text-center py-5 text-muted"><i class="fas fa-circle-notch fa-spin fa-2x mb-3"></i><p>Loading agent profiles...</p></div>';

    try {
        const token = getAuthToken();
        const response = await fetch('/api/v1/users/agents', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            cachedAgents = await response.json();
            displayAgents(cachedAgents);
        } else {
            grid.innerHTML = '<div class="w-100 text-center py-5 text-danger"><p>Failed to load agent directory.</p></div>';
        }
    } catch (e) {
        console.error("Failed to load agents", e);
        grid.innerHTML = '<div class="w-100 text-center py-5 text-danger"><p>An error occurred.</p></div>';
    }
}

// Display agent cards in the grid
function displayAgents(agents) {
    const grid = document.getElementById('agentGrid');
    const emptyState = document.getElementById('emptyState');

    if (agents.length === 0) {
        grid.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }

    grid.style.display = 'grid';
    emptyState.style.display = 'none';

    // Harmonic background colors for avatars based on name hash
    const colors = [
        'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)', // Blue
        'linear-gradient(135deg, #10b981 0%, #047857 100%)', // Emerald
        'linear-gradient(135deg, #f59e0b 0%, #b45309 100%)', // Amber
        'linear-gradient(135deg, #8b5cf6 0%, #5b21b6 100%)', // Violet
        'linear-gradient(135deg, #ec4899 0%, #be185d 100%)', // Pink
        'linear-gradient(135deg, #14b8a6 0%, #0f766e 100%)'  // Teal
    ];

    grid.innerHTML = agents.map((agent, index) => {
        const initials = agent.fullName.split(' ').map(n => n[0]).join('').toUpperCase();
        const color = colors[agent.fullName.charCodeAt(0) % colors.length];
        
        let roleDisplay = 'IT Support Staff';
        if (agent.role === 'admin') {
            roleDisplay = 'Administrator';
        }

        const specsHtml = agent.specializations && agent.specializations.length > 0
            ? agent.specializations.map(s => `<span class="spec-badge">${s}</span>`).join('')
            : '<span class="small text-muted italic">None declared</span>';

        const actionButtons = `<a href="mailto:${agent.email}" class="btn btn-outline-custom w-100 mt-auto"><i class="fas fa-envelope me-2"></i>Email Agent</a>`;

        return `
            <div class="agent-card">
                <div class="agent-card-header">
                    <div class="agent-avatar" style="background: ${color}">${initials}</div>
                    <div class="agent-meta">
                        <h3 class="agent-name" title="${agent.fullName}">${agent.fullName}</h3>
                        <span class="agent-role">${roleDisplay}</span>
                    </div>
                </div>
                <div class="agent-info-row">
                    <i class="fas fa-envelope"></i>
                    <span>${agent.email}</span>
                </div>
                <div class="agent-info-row">
                    <i class="fas fa-users"></i>
                    <span>${agent.team ? agent.team.name : 'General Support'}</span>
                </div>
                <div class="agent-specs mt-3">
                    <div class="agent-specs-label">Specialties</div>
                    <div class="spec-badges">${specsHtml}</div>
                </div>
                <div class="agent-actions">
                    ${actionButtons}
                </div>
            </div>
        `;
    }).join('');
}

// Setup searching, filtering, and resetting listeners
function setupEventListeners() {
    document.getElementById('searchAgent').addEventListener('input', applyFilters);
    document.getElementById('filterSpecialty').addEventListener('change', applyFilters);
    document.getElementById('filterTeam').addEventListener('change', applyFilters);
    document.getElementById('resetFilters').addEventListener('click', function () {
        document.getElementById('searchAgent').value = '';
        document.getElementById('filterSpecialty').value = '';
        document.getElementById('filterTeam').value = '';
        applyFilters();
    });

    // Handle raise ticket submission
    document.getElementById('raiseTicketForm').addEventListener('submit', handleRaiseTicketSubmit);

    // Duplicate Check Listener
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

// Filter programmatically using cache
function applyFilters() {
    const searchVal = document.getElementById('searchAgent').value.toLowerCase();
    const specVal = document.getElementById('filterSpecialty').value;
    const teamVal = document.getElementById('filterTeam').value;

    const filtered = cachedAgents.filter(agent => {
        // Specialty Filter
        if (specVal) {
            const specs = agent.specializations || [];
            if (!specs.some(s => s.toLowerCase() === specVal.toLowerCase())) {
                return false;
            }
        }

        // Team Filter
        if (teamVal) {
            if (!agent.team || String(agent.team.id) !== teamVal) {
                return false;
            }
        }

        // Search Query
        if (searchVal) {
            const nameMatch = agent.fullName.toLowerCase().includes(searchVal);
            const emailMatch = agent.email.toLowerCase().includes(searchVal);
            const teamMatch = agent.team && agent.team.name.toLowerCase().includes(searchVal);
            const specMatch = agent.specializations && agent.specializations.some(s => s.toLowerCase().includes(searchVal));
            return nameMatch || emailMatch || teamMatch || specMatch;
        }

        return true;
    });

    displayAgents(filtered);
}

// Open Direct Assignment Ticket Modal
window.openDirectTicketModal = function (agentId, agentName) {
    document.getElementById('raiseTicketForm').reset();
    document.getElementById('duplicateWarning').classList.add('d-none');
    document.getElementById('directAgentId').value = agentId;
    document.getElementById('directAgentName').value = agentName;

    const modal = new bootstrap.Modal(document.getElementById('raiseTicketModal'));
    modal.show();
}

// Submit Directed Ticket
async function handleRaiseTicketSubmit(e) {
    e.preventDefault();

    // Check for Demo Mode if body has class
    if (document.body.classList.contains('demo-mode')) {
        const formModal = bootstrap.Modal.getInstance(document.getElementById('raiseTicketModal'));
        if (formModal) formModal.hide();
        const restrictedModal = new bootstrap.Modal(document.getElementById('restrictedActionModal'));
        restrictedModal.show();
        return;
    }

    const btn = document.getElementById('submitTicketBtn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Submitting...';

    const agentId = document.getElementById('directAgentId').value;
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
                description: description,
                assigned_to_id: parseInt(agentId)
            })
        });

        const data = await response.json();

        if (response.ok) {
            bootstrap.Modal.getInstance(document.getElementById('raiseTicketModal')).hide();
            showToast('Directed ticket raised successfully! Redirecting...', 'success');
            setTimeout(() => {
                window.location.href = '/dashboard/employee';
            }, 1500);
        } else {
            alert(data.error || 'Failed to submit ticket');
        }
    } catch (e) {
        console.error("Submit directed ticket error", e);
        alert('An error occurred.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Sidebar toggle on mobile
window.toggleSidebar = function () {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
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

// Show Toast Alert
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position: fixed; bottom: 24px; right: 24px; z-index: 9999; display: flex; flex-direction: column; gap: 12px;';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const colors = {
        success: { bg: 'rgba(16, 185, 129, 0.9)', icon: 'check-circle' },
        error: { bg: 'rgba(239, 68, 68, 0.9)', icon: 'exclamation-circle' },
        info: { bg: 'rgba(59, 130, 246, 0.9)', icon: 'info-circle' }
    };
    const style = colors[type] || colors.info;

    toast.style.cssText = `background: ${style.bg}; color: white; padding: 12px 20px; border-radius: 12px; box-shadow: var(--shadow-lg); font-weight: 500; display: flex; align-items: center; gap: 10px; transform: translateX(120%); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); backdrop-filter: blur(8px); min-width: 300px;`;
    toast.innerHTML = `<i class="fas fa-${style.icon}"></i><span>${message}</span>`;
    container.appendChild(toast);

    requestAnimationFrame(() => {
        toast.style.transform = 'translateX(0)';
    });

    setTimeout(() => {
        toast.style.transform = 'translateX(120%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
