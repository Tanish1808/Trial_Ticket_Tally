// IT Calendar Management JavaScript
if (!requireAuth()) {
    // Will redirect if not authenticated
}

const currentUser = getCurrentUser();
const isAdmin = currentUser && currentUser.role === 'admin';

document.addEventListener('DOMContentLoaded', function () {
    // Show/hide Admin create action button
    const createBtn = document.getElementById('createEventBtn');
    if (createBtn && isAdmin) {
        createBtn.classList.remove('d-none');
    }

    initializeCalendar();
});

let calendarInstance;

function initializeCalendar() {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) return;

    calendarInstance = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        editable: false, // Drag and drop not enabled for simplicity
        selectable: isAdmin, // Only admins can select slot to create event
        events: fetchEventsForCalendar,
        
        eventClick: function (info) {
            const eventObj = info.event;
            const props = eventObj.extendedProps;
            
            if (isAdmin) {
                // Admins edit/delete event
                showEditEventModal(eventObj);
            } else {
                // Employees / IT Staff view event details
                showEventDetailsModal(eventObj);
            }
        },
        
        select: function (info) {
            if (isAdmin) {
                showAddEventModal(info.startStr, info.endStr);
            }
        }
    });

    calendarInstance.render();
}

async function fetchEventsForCalendar(fetchInfo, successCallback, failureCallback) {
    try {
        const response = await fetch('/api/v1/events', {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (response.ok) {
            const events = await response.json();
            
            // Map our Event schema to FullCalendar format
            const mappedEvents = events.map(e => ({
                id: e.id,
                title: e.title,
                start: e.startTime || e.start_time,
                end: e.endTime || e.end_time,
                className: `fc-event-${e.eventType || e.event_type}`,
                extendedProps: {
                    description: e.description,
                    eventType: e.eventType || e.event_type,
                    createdBy: e.createdBy,
                    createdById: e.createdById
                }
            }));
            
            successCallback(mappedEvents);
        } else {
            failureCallback();
        }
    } catch (e) {
        console.error("Failed to load events", e);
        failureCallback(e);
    }
}

function showAddEventModal(startStr = null, endStr = null) {
    const form = document.getElementById('eventForm');
    form.reset();
    
    document.getElementById('eventId').value = '';
    document.getElementById('eventModalTitle').textContent = 'Create IT Event';
    document.getElementById('deleteEventBtn').classList.add('d-none');
    
    // Set default times if slot selected
    if (startStr) {
        // FullCalendar ISO date might not include time (e.g. 2026-06-15)
        // Format to HTML datetime-local format: YYYY-MM-DDTHH:MM
        let startTime = startStr;
        if (startStr.length === 10) startTime = `${startStr}T09:00`;
        else startTime = startStr.substring(0, 16);
        document.getElementById('eventStartTime').value = startTime;
    }
    
    if (endStr) {
        let endTime = endStr;
        if (endStr.length === 10) endTime = `${endStr}T17:00`;
        else endTime = endStr.substring(0, 16);
        document.getElementById('eventEndTime').value = endTime;
    }

    const modal = new bootstrap.Modal(document.getElementById('eventModal'));
    modal.show();
    
    form.onsubmit = handleSaveEvent;
}

function showEditEventModal(eventObj) {
    const form = document.getElementById('eventForm');
    form.reset();

    document.getElementById('eventId').value = eventObj.id;
    document.getElementById('eventModalTitle').textContent = 'Edit IT Event';
    document.getElementById('deleteEventBtn').classList.remove('d-none');

    document.getElementById('eventTitle').value = eventObj.title;
    document.getElementById('eventDescription').value = eventObj.extendedProps.description || '';
    document.getElementById('eventType').value = eventObj.extendedProps.eventType;
    
    // Format dates to YYYY-MM-DDTHH:MM
    const start = new Date(eventObj.start);
    document.getElementById('eventStartTime').value = formatLocalDateTime(start);
    
    if (eventObj.end) {
        const end = new Date(eventObj.end);
        document.getElementById('eventEndTime').value = formatLocalDateTime(end);
    }

    const modal = new bootstrap.Modal(document.getElementById('eventModal'));
    modal.show();

    form.onsubmit = handleSaveEvent;
}

function showEventDetailsModal(eventObj) {
    document.getElementById('viewEventTitle').textContent = eventObj.title;
    document.getElementById('viewEventDescription').textContent = eventObj.extendedProps.description || 'No description provided.';
    
    // Categories display
    const type = eventObj.extendedProps.eventType;
    const badge = document.getElementById('viewEventBadge');
    
    const types = {
        maintenance: { text: 'IT Maintenance', class: 'bg-danger' },
        training: { text: 'IT Staff Training', class: 'bg-primary' },
        system_update: { text: 'System Update / Release', class: 'bg-success' },
        other: { text: 'Other IT Event', class: 'bg-warning text-dark' }
    };
    
    const config = types[type] || { text: 'IT Event', class: 'bg-secondary' };
    badge.innerHTML = `<span class="badge ${config.class} fs-6">${config.text}</span>`;

    // Time format
    document.getElementById('viewEventStart').textContent = new Date(eventObj.start).toLocaleString();
    document.getElementById('viewEventEnd').textContent = eventObj.end ? new Date(eventObj.end).toLocaleString() : 'N/A';
    
    document.getElementById('viewEventCreator').textContent = eventObj.extendedProps.createdBy || 'System';

    const modal = new bootstrap.Modal(document.getElementById('eventDetailsModal'));
    modal.show();
}

async function handleSaveEvent(e) {
    e.preventDefault();

    const eventId = document.getElementById('eventId').value;
    const title = document.getElementById('eventTitle').value.trim();
    const description = document.getElementById('eventDescription').value.trim();
    const eventType = document.getElementById('eventType').value;
    const startTime = new Date(document.getElementById('eventStartTime').value).toISOString();
    const endTime = new Date(document.getElementById('eventEndTime').value).toISOString();

    if (new Date(endTime) <= new Date(startTime)) {
        alert("End time must be after start time");
        return;
    }

    const payload = {
        title,
        description,
        event_type: eventType,
        start_time: startTime,
        end_time: endTime
    };

    const isEdit = !!eventId;
    const url = isEdit ? `/api/v1/events/${eventId}` : '/api/v1/events';
    const method = isEdit ? 'PATCH' : 'POST';

    try {
        const response = await fetch(url, {
            method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const modalEl = document.getElementById('eventModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();

            calendarInstance.refetchEvents();
            alert(isEdit ? "Event updated successfully" : "Event created successfully");
        } else {
            const err = await response.json();
            alert(err.error || "Failed to save event");
        }
    } catch (err) {
        console.error(err);
        alert("Error saving event");
    }
}

async function handleDeleteEvent() {
    const eventId = document.getElementById('eventId').value;
    if (!eventId) return;

    if (!confirm("Are you sure you want to delete this event?")) return;

    try {
        const response = await fetch(`/api/v1/events/${eventId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (response.ok) {
            const modalEl = document.getElementById('eventModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();

            calendarInstance.refetchEvents();
            alert("Event deleted successfully");
        } else {
            alert("Failed to delete event");
        }
    } catch (e) {
        console.error(e);
        alert("Error deleting event");
    }
}

// Helpers
function formatLocalDateTime(date) {
    const tzOffset = date.getTimezoneOffset() * 60000; // offset in milliseconds
    const localISOTime = (new Date(date - tzOffset)).toISOString().slice(0, 16);
    return localISOTime;
}

function goBackToDashboard() {
    if (currentUser) {
        if (currentUser.role === 'admin') window.location.href = '/dashboard/admin';
        else if (currentUser.role === 'it_staff') window.location.href = '/dashboard/it-staff';
        else window.location.href = '/dashboard/employee';
    } else {
        window.location.href = '/';
    }
}
