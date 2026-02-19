/* ==========================================================================
   Projects Management JavaScript
   Complete project tracking, team assignment, and deadline management (API Integration)
   ========================================================================== */

// Check authentication - Admin only
if (!requireAuth()) {
    // Will redirect if not authenticated
}

const currentUser = getCurrentUser();
if (!currentUser || currentUser.role !== 'admin') {
    alert('Access denied. Administrator privileges required.');
    window.location.href = 'admin-dashboard.html';
}

// Initialize page
document.addEventListener('DOMContentLoaded', function () {
    initializeProjectsPage();
    loadProjects();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // START: Removed duplicate event listener to prevent double submission
    // document.getElementById('addProjectForm').addEventListener('submit', handleAddProject);
    // END: Removed duplicate event listener

    // Set default dates
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('projectStartDate').value = today;

    const nextMonth = new Date();
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    document.getElementById('projectDeadline').value = nextMonth.toISOString().split('T')[0];

    setupTeamAutocomplete();
}

// Global Team Members State
let currentTeamMembers = [];

function setupTeamAutocomplete() {
    const input = document.getElementById('teamInput');
    const suggestionsList = document.getElementById('teamSuggestions');
    let debounceTimer;

    // Handle Input Typing
    input.addEventListener('input', function () {
        const query = this.value.trim();

        clearTimeout(debounceTimer);

        if (query.length < 2) {
            suggestionsList.style.display = 'none';
            return;
        }

        debounceTimer = setTimeout(async () => {
            try {
                const response = await fetch(`/api/v1/users?search=${encodeURIComponent(query)}&role=employee`, {
                    headers: { 'Authorization': `Bearer ${getAuthToken()}` }
                });

                if (response.ok) {
                    const users = await response.json();
                    renderSuggestions(users);
                }
            } catch (e) {
                console.error("Search error", e);
            }
        }, 300); // 300ms debounce
    });

    // Handle Enter Key (Add Email Directly)
    input.addEventListener('keydown', async function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const email = this.value.trim();
            if (email) {
                // Check if valid user first
                await validateAndAddUser(email);
            }
        }
    });

    // Hide suggestions on click outside
    document.addEventListener('click', function (e) {
        if (!input.contains(e.target) && !suggestionsList.contains(e.target)) {
            suggestionsList.style.display = 'none';
        }
    });
}

function renderSuggestions(users) {
    const list = document.getElementById('teamSuggestions');
    list.innerHTML = '';

    if (users.length === 0) {
        list.style.display = 'none';
        return;
    }

    users.forEach(user => {
        // Don't show already added members
        if (currentTeamMembers.some(m => m.email === user.email)) return;

        const li = document.createElement('li');
        li.className = 'list-group-item list-group-item-action curspr-pointer';
        li.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="member-avatar me-2" style="width: 24px; height: 24px; font-size: 10px;">
                    ${user.full_name.split(' ').map(n => n[0]).join('')}
                </div>
                <div>
                    <div>${user.full_name}</div>
                    <small class="text-muted">${user.email}</small>
                </div>
            </div>
        `;
        li.onclick = () => {
            addTeamMember(user);
            document.getElementById('teamInput').value = '';
            list.style.display = 'none';
        };
        list.appendChild(li);
    });

    list.style.display = users.length > 0 ? 'block' : 'none';
}

async function validateAndAddUser(email) {
    // 1. Check if already added
    if (currentTeamMembers.some(m => m.email.toLowerCase() === email.toLowerCase())) {
        document.getElementById('teamInput').value = ''; // Clear duplicate
        return;
    }

    try {
        // 2. Check API
        const response = await fetch(`/api/v1/users?search=${encodeURIComponent(email)}`, {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (response.ok) {
            const users = await response.json();
            const exactMatch = users.find(u => u.email.toLowerCase() === email.toLowerCase());

            if (exactMatch) {
                addTeamMember(exactMatch);
                document.getElementById('teamInput').value = '';
            } else {
                showUserNotFound(email);
            }
        }
    } catch (e) {
        console.error("Validation error", e);
    }
}

function showUserNotFound(email) {
    document.getElementById('notFoundEmail').textContent = email;
    const modal = new bootstrap.Modal(document.getElementById('userNotFoundModal'));
    modal.show();
}

function addTeamMember(user) {
    currentTeamMembers.push({
        email: user.email,
        name: user.full_name || user.email // Fallback
    });
    renderChips();
    // Update hidden input for legacy compliance if needed (though we use currentTeamMembers in submit)
    document.getElementById('projectTeam').value = JSON.stringify(currentTeamMembers);
}

function removeTeamMember(email) {
    currentTeamMembers = currentTeamMembers.filter(m => m.email !== email);
    renderChips();
    document.getElementById('projectTeam').value = JSON.stringify(currentTeamMembers);
}

function renderChips() {
    const container = document.getElementById('teamChips');
    container.innerHTML = currentTeamMembers.map(member => `
        <span class="badge bg-light text-dark border d-flex align-items-center gap-2 p-2">
            <div class="member-avatar" style="width: 20px; height: 20px; font-size: 8px;">
                ${member.name ? member.name.split(' ').map(n => n[0]).join('') : '?'}
            </div>
            ${member.name}
            <i class="fas fa-times text-muted cursor-pointer" onclick="removeTeamMember('${member.email}')"></i>
        </span>
    `).join('');
}

// Initialize page
function initializeProjectsPage() {
    // Page is ready
}

// Ticket Cache (for Projects now)
let projectsCache = [];

function getProjects() {
    return projectsCache;
}

// Fetch Projects from API
async function loadProjects() {
    try {
        const response = await fetch('/api/v1/projects', {
            headers: { 'Authorization': `Bearer ${getAuthToken()} ` }
        });

        if (response.ok) {
            projectsCache = await response.json();
            updateStatistics(projectsCache);
            displayProjects(projectsCache);
        } else {
            console.error("Failed to fetch projects");
        }
    } catch (e) {
        console.error("Error fetching projects", e);
    }
}

// Update statistics
function updateStatistics(projects) {
    const total = projects.length;
    const active = projects.filter(p => p.status === 'Active').length;
    const completed = projects.filter(p => p.status === 'Completed').length;

    // Calculate deadline this week
    const today = new Date();
    const weekFromNow = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
    const upcoming = projects.filter(p => {
        if (p.status === 'Completed') return false;
        if (!p.deadline) return false;
        const deadline = new Date(p.deadline);
        return deadline >= today && deadline <= weekFromNow;
    }).length;

    document.getElementById('totalProjects').textContent = total;
    document.getElementById('activeProjects').textContent = active;
    document.getElementById('completedProjects').textContent = completed;
    document.getElementById('upcomingDeadlines').textContent = upcoming;
}

// Display projects
function displayProjects(projects) {
    const grid = document.getElementById('projectsGrid');
    const emptyState = document.getElementById('emptyState');

    if (projects.length === 0) {
        grid.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }

    emptyState.style.display = 'none';

    // Sort by deadline (closest first)
    projects.sort((a, b) => {
        if (!a.deadline) return 1;
        if (!b.deadline) return -1;
        return new Date(a.deadline) - new Date(b.deadline);
    });

    grid.innerHTML = projects.map(project => createProjectCard(project)).join('');
}

// Create project card HTML
function createProjectCard(project) {
    const statusClass = project.status.toLowerCase().replace(' ', '-');
    const deadlineBadge = getDeadlineBadge(project.deadline, project.status);
    const teamMembers = project.team || [];
    const progress = project.progress || 0;

    return `
    <div class="project-card status-${statusClass}">
            <div class="project-header">
                <div>
                    <h3 class="project-title">${project.name}</h3>
                    <span class="project-status ${statusClass}">${project.status}</span>
                </div>
            </div>
            
            <p class="project-description">${project.description || 'No description'}</p>
            
            <div class="project-meta">
                <div class="meta-item">
                    <div class="meta-icon">
                        <i class="fas fa-calendar"></i>
                    </div>
                    <div>
                        <span class="meta-label">Start:</span>
                        <span class="meta-value">${project.startDate ? formatDate(project.startDate) : 'N/A'}</span>
                    </div>
                </div>
                
                <div class="meta-item">
                    <div class="meta-icon">
                        <i class="fas fa-flag-checkered"></i>
                    </div>
                    <div>
                        <span class="meta-label">Deadline:</span>
                        ${deadlineBadge}
                    </div>
                </div>
                
                <div class="meta-item">
                    <div class="meta-icon">
                        <i class="fas fa-exclamation-circle"></i>
                    </div>
                    <div>
                        <span class="meta-label">Priority:</span>
                        <span class="priority-badge priority-${project.priority.toLowerCase()}">${project.priority}</span>
                    </div>
                </div>
            </div>
            
            <div class="team-members">
                ${teamMembers.slice(0, 5).map(member => {
        const initials = member.name ? member.name.split(' ').map(n => n[0]).join('').toUpperCase() : '?';
        return `<div class="member-avatar" title="${member.name || member.email}">${initials}</div>`;
    }).join('')}
                ${teamMembers.length > 5 ? `<div class="member-avatar">+${teamMembers.length - 5}</div>` : ''}
                ${teamMembers.length === 0 ? '<span class="text-muted small">No team assigned</span>' : ''}
            </div>
            
            <div class="progress-section">
                <div class="progress-label">
                    <span>Progress</span>
                    <span><strong>${progress}%</strong></span>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar-fill" style="width: ${progress}%"></div>
                </div>
            </div>
            
            <div class="project-actions">
                <button class="btn btn-sm btn-primary-custom flex-fill" onclick="viewProject('${project.id}')">
                    <i class="fas fa-eye me-1"></i>View Details
                </button>
                <button class="btn btn-sm btn-outline-custom" onclick="editProject('${project.id}')" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteProject('${project.id}')" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `;
}

// Get deadline badge with urgency indicator
function getDeadlineBadge(deadline, status) {
    if (status === 'Completed') {
        return `<span class="deadline-badge normal">Completed</span>`;
    }

    if (!deadline) {
        return `<span class="deadline-badge normal">No Deadline</span>`;
    }

    const deadlineDate = new Date(deadline);
    const today = new Date();
    const daysUntil = Math.ceil((deadlineDate - today) / (1000 * 60 * 60 * 24));

    let badgeClass = 'normal';
    let text = formatDate(deadline);

    if (daysUntil < 0) {
        badgeClass = 'urgent';
        text = `Overdue by ${Math.abs(daysUntil)} days`;
    } else if (daysUntil === 0) {
        badgeClass = 'urgent';
        text = 'Due Today!';
    } else if (daysUntil <= 3) {
        badgeClass = 'urgent';
        text = `${daysUntil} days left`;
    } else if (daysUntil <= 7) {
        badgeClass = 'soon';
        text = `${daysUntil} days left`;
    }

    return `<span class="deadline-badge ${badgeClass}"><i class="fas fa-clock me-1"></i>${text}</span>`;
}

// Filter projects by status
function filterProjects(status) {
    const projects = getProjects();
    const filtered = status === 'all' ? projects : projects.filter(p => p.status === status);

    displayProjects(filtered);

    // Update active tab
    document.querySelectorAll('#projectFilterTabs .nav-link').forEach(link => {
        link.classList.remove('active');
    });
    if (event && event.target) {
        event.target.closest('.nav-link').classList.add('active');
    }
}

// Show add project modal
function showAddProjectModal() {
    const form = document.getElementById('addProjectForm');
    form.reset();
    form.onsubmit = handleAddProject; // Reset submit handler in case it was changed by edit
    currentTeamMembers = []; // Reset team
    renderChips(); // Clear chips

    document.querySelector('#addProjectModal .modal-title').innerHTML = '<i class="fas fa-plus-circle me-2"></i>Create New Project';

    // Set Status Options for Create (Only Active & Planning)
    const statusSelect = document.getElementById('projectStatus');
    statusSelect.innerHTML = `
    <option value="Planning">Planning</option>
        <option value="Active" selected>Active</option>
`;

    const modal = new bootstrap.Modal(document.getElementById('addProjectModal'));
    modal.show();
}

// Validate Project Dates
function validateProjectDates(startDate, deadline) {
    if (!startDate || !deadline) return true; // Let required attribute handle empty
    if (new Date(deadline) < new Date(startDate)) {
        const modal = new bootstrap.Modal(document.getElementById('dateConflictModal'));
        modal.show();
        return false;
    }
    return true;
}

// Handle add project
async function handleAddProject(e) {
    e.preventDefault();

    // Check for pending team input and Auto-Add
    const teamInput = document.getElementById('teamInput');
    if (teamInput && teamInput.value.trim().length > 0) {
        const email = teamInput.value.trim();
        await validateAndAddUser(email);

        // If input is still there, it meant validation failed (modal showed)
        if (teamInput.value.trim().length > 0) {
            return; // Stop submission
        }
    }

    // Prevent Double Submission
    const submitBtn = document.querySelector('#addProjectForm button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Creating...';

    const name = document.getElementById('projectName').value;
    const description = document.getElementById('projectDescription').value;
    const status = document.getElementById('projectStatus').value;
    const priority = document.getElementById('projectPriority').value;
    const startDate = document.getElementById('projectStartDate').value;
    const deadline = document.getElementById('projectDeadline').value;

    // Use the chips array instead of parsing text
    const team = currentTeamMembers;

    // Validate Dates
    if (!validateProjectDates(startDate, deadline)) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-save me-2"></i>Create Project';
        return;
    }

    const projectData = {
        name,
        description,
        status,
        priority,
        startDate,
        deadline,
        team
    };

    try {
        const response = await fetch('/api/v1/projects', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()} `
            },
            body: JSON.stringify(projectData)
        });

        if (response.ok) {
            alert(`Project "${name}" created successfully!`);
            const modal = bootstrap.Modal.getInstance(document.getElementById('addProjectModal'));
            modal.hide();
            document.getElementById('addProjectForm').reset();
            loadProjects();
        } else {
            const err = await response.json();
            alert(err.error || "Failed to create project");
        }
    } catch (e) {
        console.error("Error creating project", e);
        alert("Error creating project");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-save me-2"></i>Create Project';
    }
}

// View project details
function viewProject(projectId) {
    const projects = getProjects();
    const project = projects.find(p => p.id == projectId);

    if (!project) {
        alert('Project not found');
        return;
    }

    const modalBody = document.getElementById('viewProjectBody');
    document.getElementById('viewProjectTitle').textContent = project.name;

    const teamMembers = project.team || [];
    const deadlineBadge = getDeadlineBadge(project.deadline, project.status);

    modalBody.innerHTML = `
    <div class="row">
            <div class="col-md-8">
                <div class="mb-4">
                    <h6 class="text-muted text-uppercase mb-2">Description</h6>
                    <p style="white-space: pre-wrap;">${project.description || 'No description'}</p>
                </div>
                
                <div class="mb-4">
                    <h6 class="text-muted text-uppercase mb-3">Team Members (${teamMembers.length})</h6>
                    ${teamMembers.length > 0 ? `
                        <div class="row g-3">
                            ${teamMembers.map(member => `
                                <div class="col-md-6">
                                    <div class="d-flex align-items-center gap-3 p-3" style="background: var(--surface-elevated); border-radius: var(--radius-md);">
                                        <div class="member-avatar" style="width: 3rem; height: 3rem; font-size: 1.125rem;">
                                            ${member.name ? member.name.split(' ').map(n => n[0]).join('').toUpperCase() : '?'}
                                        </div>
                                        <div>
                                            <div class="fw-bold">${member.name || 'Unknown'}</div>
                                            <div class="text-muted small">${member.email}</div>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : '<p class="text-muted">No team members assigned</p>'}
                </div>
            </div>
            
            <div class="col-md-4">
                <div class="card-custom mb-3">
                    <h6 class="text-muted text-uppercase mb-3">Project Info</h6>
                    
                    <div class="mb-3">
                        <small class="text-muted">Status</small>
                        <div class="mt-1">
                            <span class="project-status ${project.status.toLowerCase().replace(' ', '-')}">${project.status}</span>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <small class="text-muted">Priority</small>
                        <div class="mt-1">
                            <span class="priority-badge priority-${project.priority.toLowerCase()}">${project.priority}</span>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <small class="text-muted">Progress</small>
                        <div class="mt-2">
                            <div class="progress-bar-container">
                                <div class="progress-bar-fill" style="width: ${project.progress}%"></div>
                            </div>
                            <div class="text-end mt-1"><strong>${project.progress}%</strong></div>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <small class="text-muted">Start Date</small>
                        <div class="mt-1 fw-bold">${project.startDate ? formatDate(project.startDate) : 'N/A'}</div>
                    </div>
                    
                    <div class="mb-3">
                        <small class="text-muted">Deadline</small>
                        <div class="mt-1">${deadlineBadge}</div>
                    </div>
                    
                    <div class="mb-3">
                        <small class="text-muted">Created</small>
                        <div class="mt-1 text-muted small">${formatDate(project.createdAt)}</div>
                    </div>
                </div>
                
                <div class="d-grid gap-2">
                    <button class="btn btn-primary-custom" onclick="editProject('${project.id}')">
                        <i class="fas fa-edit me-2"></i>Edit Project
                    </button>
                    <button class="btn btn-outline-custom" onclick="updateProgress('${project.id}')">
                        <i class="fas fa-tasks me-2"></i>Update Progress
                    </button>
                </div>
            </div>
        </div>
    `;

    // Wire up functions inside modal context if needed, but they are global so should work.

    const modal = new bootstrap.Modal(document.getElementById('viewProjectModal'));
    modal.show();
}

// Helper to handle completion confirmation
function confirmCompletion(onConfirm) {
    const modalEl = document.getElementById('completionModal');
    const modal = new bootstrap.Modal(modalEl);
    const confirmBtn = document.getElementById('confirmCompletionBtn');

    // Clear previous listeners
    const newBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newBtn, confirmBtn);

    newBtn.addEventListener('click', function () {
        modal.hide();
        onConfirm();
    });

    modal.show();
}

// Edit project
function editProject(projectId) {
    try {
        console.log('editProject called with ID:', projectId, 'Type:', typeof projectId);
        const projects = getProjects();
        console.log('Current projects cache:', projects);

        // Loose equality check for ID match to handle string/number differences
        const project = projects.find(p => p.id == projectId);
        console.log('Found project:', project);

        if (!project) {
            console.error('Project not found in cache for ID:', projectId);
            alert('Error: Project not found. Please refresh the page.');
            return;
        }

        // Close view modal if open
        const viewModalEl = document.getElementById('viewProjectModal');
        if (viewModalEl) {
            const viewModal = bootstrap.Modal.getInstance(viewModalEl);
            if (viewModal) viewModal.hide();
        }

        // Populate form
        document.getElementById('projectName').value = project.name;
        document.getElementById('projectDescription').value = project.description || '';

        // Set Status Options for Edit
        const statusSelect = document.getElementById('projectStatus');

        if (project.status === 'Completed') {
            // Looking at file content read in 472, the logic was:
            statusSelect.innerHTML = `<option value="Completed" selected>Completed</option>`;
            statusSelect.disabled = true;
        } else {
            let options = `
            <option value="Active">Active</option>
            <option value="On Hold">On Hold</option>
            <option value="Completed">Completed</option>
            `;

            // Allow keeping it in Planning if it is currently Planning
            if (project.status === 'Planning') {
                options = `<option value="Planning">Planning</option>` + options;
            }

            statusSelect.innerHTML = options;
            statusSelect.disabled = false;
        }

        document.getElementById('projectStatus').value = project.status;
        document.getElementById('projectPriority').value = project.priority;
        document.getElementById('projectStartDate').value = project.startDate || '';
        document.getElementById('projectDeadline').value = project.deadline || '';

        // Populate Chips from Team
        currentTeamMembers = project.team ? project.team.map(m => ({ email: m.email, name: m.name || m.email })) : [];
        renderChips();

        // [NEW] Disable all fields if Completed
        const isCompleted = project.status === 'Completed';
        const fieldsToDisable = ['projectName', 'projectDescription', 'projectPriority', 'projectStartDate', 'projectDeadline', 'projectStatus'];
        const submitBtn = document.querySelector('#addProjectForm button[type="submit"]');

        fieldsToDisable.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.disabled = isCompleted;
        });

        // Handle Edit Button/Submit Button visibility/state
        if (submitBtn) {
            submitBtn.disabled = isCompleted;
            submitBtn.textContent = isCompleted ? "Project Completed (Read-Only)" : "Update Project";
        }

        // Change form to edit mode
        const form = document.getElementById('addProjectForm');
        form.onsubmit = async function (e) {
            e.preventDefault();

            // Check for pending team input and Auto-Add
            const teamInput = document.getElementById('teamInput');
            if (teamInput && teamInput.value.trim().length > 0) {
                const email = teamInput.value.trim();
                await validateAndAddUser(email);

                // If input is still there, it meant validation failed (modal showed)
                if (teamInput.value.trim().length > 0) {
                    return; // Stop submission
                }
            }

            // Prevent Double Submission
            const submitBtn = document.querySelector('#addProjectForm button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Updating...';


            const getFormData = () => {
                const name = document.getElementById('projectName').value;
                const description = document.getElementById('projectDescription').value;
                const status = document.getElementById('projectStatus').value;
                const priority = document.getElementById('projectPriority').value;
                const startDate = document.getElementById('projectStartDate').value;
                const deadline = document.getElementById('projectDeadline').value;

                // Use Chips
                const team = currentTeamMembers;

                return { name, description, status, priority, startDate, deadline, team };
            };

            const data = getFormData();

            // Validate Dates
            if (!validateProjectDates(data.startDate, data.deadline)) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-save me-2"></i>Update Project';
                return;
            }

            const submitUpdate = async (updateData) => {
                try {
                    const response = await fetch(`/api/v1/projects/${projectId}`, {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${getAuthToken()}`
                        },
                        body: JSON.stringify(updateData)
                    });

                    if (response.ok) {
                        alert('Project updated successfully!');
                        const modal = bootstrap.Modal.getInstance(document.getElementById('addProjectModal'));
                        modal.hide();
                        form.reset();
                        form.onsubmit = handleAddProject; // Restore default handler
                        loadProjects();
                    } else {
                        const err = await response.json();
                        alert(err.error || "Failed to update project");
                    }
                } catch (e) {
                    console.error(e);
                    alert('Error updating project: ' + e.message);
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-save me-2"></i>Update Project';
                }
            };



            // Check for completion status
            if (data.status === 'Completed' && project.status !== 'Completed') {
                data.progress = 100; // Auto 100% on completion
                confirmCompletion(() => submitUpdate(data));
            } else {
                submitUpdate(data);
            }
        };

        // Show modal
        const modalEl = document.getElementById('addProjectModal');
        if (!modalEl) {
            console.error('Add Project Modal element not found!');
            return;
        }

        document.querySelector('#addProjectModal .modal-title').innerHTML = '<i class="fas fa-edit me-2"></i>Edit Project';

        try {
            const modal = new bootstrap.Modal(modalEl);
            console.log('Showing edit modal...');
            modal.show();
        } catch (e) {
            console.error('Failed to show modal:', e);
        }

        // Reset title when modal closes
        document.getElementById('addProjectModal').addEventListener('hidden.bs.modal', function () {
            document.querySelector('#addProjectModal .modal-title').innerHTML = '<i class="fas fa-plus-circle me-2"></i>Create New Project';
            form.onsubmit = handleAddProject;
        }, { once: true });
    } catch (err) {
        console.error("CRASH in editProject:", err);
        alert("An error occurred while trying to edit the project: " + err.message);
    }
}

// Update progress
async function updateProgress(projectId) {
    const projects = getProjects();
    const project = projects.find(p => p.id == projectId);

    if (!project) return;

    if (project.status === 'Completed') {
        // Show Already Completed Modal
        const modal = new bootstrap.Modal(document.getElementById('alreadyCompletedModal'));
        modal.show();
        return;
    }

    const newProgress = prompt(`Enter progress percentage for "${project.name}" (0-100):`, project.progress);

    if (newProgress !== null) {
        const progress = parseInt(newProgress);
        if (!isNaN(progress) && progress >= 0 && progress <= 100) {

            const performUpdate = async (statusUpdate) => {
                const updateData = { progress };
                if (statusUpdate) updateData.status = statusUpdate;

                try {
                    const response = await fetch(`/api/v1/projects/${projectId}`, {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${getAuthToken()}`
                        },
                        body: JSON.stringify(updateData)
                    });

                    if (response.ok) {
                        loadProjects();
                        // Refresh view modal if open
                        const viewModal = document.getElementById('viewProjectModal');
                        if (viewModal.classList.contains('show')) {
                            // Re-open (simple way to refresh data)
                            viewModal.classList.remove('show'); // Force re-render trick or just close
                            const modal = bootstrap.Modal.getInstance(viewModal);
                            modal.hide();
                            setTimeout(() => viewProject(projectId), 500);
                        }
                    } else {
                        alert('Failed to update progress');
                    }
                } catch (e) {
                    console.error(e);
                }
            };

            if (progress === 100) {
                // Trigger Smart Completion
                confirmCompletion(() => performUpdate('Completed'));
            } else {
                performUpdate(null);
            }

        } else {
            alert('Please enter a valid number between 0 and 100');
        }
    }
}

// Delete project
function deleteProject(projectId) {
    const projects = getProjects();
    const project = projects.find(p => p.id == projectId);

    if (!project) return;

    // Set modal content
    document.getElementById('deleteProjectName').textContent = project.name;

    // Set up confirm button
    const confirmBtn = document.getElementById('confirmDeleteBtn');

    // Remove existing listeners to avoid duplicates
    const newBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newBtn, confirmBtn);

    newBtn.addEventListener('click', () => performDelete(projectId));

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('deleteProjectModal'));
    modal.show();
}

async function performDelete(projectId) {
    try {
        const response = await fetch(`/api/v1/projects/${projectId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${getAuthToken()} ` }
        });

        if (response.ok) {
            // Close modal
            const modalEl = document.getElementById('deleteProjectModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            modal.hide();

            showToast('Project deleted successfully'); // Assuming showToast exists or fallback to alert
            loadProjects();
        } else {
            alert('Failed to delete project');
        }
    } catch (e) {
        console.error(e);
        alert('Error deleting project');
    }
}

// Go back to dashboard
function goBackToDashboard() {
    window.location.href = '/dashboard/admin';
}