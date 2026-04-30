/**
 * Portal Attendee Tag Input Widget
 * Provides a Select2/tags-style multi-select for choosing same-company attendees.
 */
function _initAttendeeWidget() {
    const searchInput = document.getElementById('attendee_search');
    const dropdown = document.getElementById('attendee-dropdown');
    const tagsContainer = document.getElementById('attendee-tags');
    const hiddenInput = document.getElementById('attendee_ids');

    if (!searchInput || !dropdown || !tagsContainer || !hiddenInput) return;

    const selected = new Map(); // id -> {id, name, email}
    let debounceTimer = null;

    function updateHiddenInput() {
        hiddenInput.value = Array.from(selected.keys()).join(',');
    }

    function addTag(att) {
        if (selected.has(att.id)) return;
        selected.set(att.id, att);
        updateHiddenInput();

        const tag = document.createElement('span');
        tag.className = 'badge bg-primary d-inline-flex align-items-center gap-1';
        tag.dataset.id = att.id;
        tag.innerHTML =
            '<i class="fa fa-user"></i> ' +
            escapeHtml(att.name) +
            ' <button type="button" class="btn-close btn-close-white ms-1" style="font-size:0.6em;" aria-label="Remove"></button>';

        tag.querySelector('.btn-close').addEventListener('click', function (e) {
            e.preventDefault();
            selected.delete(att.id);
            tag.remove();
            updateHiddenInput();
        });

        tagsContainer.appendChild(tag);
    }

    function escapeHtml(text) {
        const d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    }

    function showDropdown(attendees) {
        dropdown.innerHTML = '';
        if (!attendees.length) {
            const item = document.createElement('div');
            item.className = 'dropdown-item text-muted disabled';
            item.textContent = 'No results found';
            dropdown.appendChild(item);
        } else {
            attendees.forEach(function (att) {
                if (selected.has(att.id)) return;
                const item = document.createElement('a');
                item.className = 'dropdown-item';
                item.href = '#';
                item.innerHTML =
                    '<i class="fa fa-user-o me-1"></i>' +
                    escapeHtml(att.name) +
                    (att.email ? ' <small class="text-muted">(' + escapeHtml(att.email) + ')</small>' : '');
                item.addEventListener('mousedown', function (e) {
                    e.preventDefault();
                    addTag(att);
                    searchInput.value = '';
                    dropdown.classList.remove('show');
                });
                dropdown.appendChild(item);
            });
        }
        dropdown.classList.add('show');
    }

    function doSearch(query) {
        fetch('/my/booking/attendees/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: { query: query },
            }),
        })
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
            var attendees = (data.result && data.result.attendees) || [];
            showDropdown(attendees);
        })
        .catch(function () {
            dropdown.classList.remove('show');
        });
    }

    searchInput.addEventListener('input', function () {
        const q = searchInput.value.trim();
        clearTimeout(debounceTimer);
        if (q.length < 1) {
            dropdown.classList.remove('show');
            return;
        }
        debounceTimer = setTimeout(function () {
            doSearch(q);
        }, 300);
    });

    searchInput.addEventListener('focus', function () {
        const q = searchInput.value.trim();
        if (q.length >= 1) {
            doSearch(q);
        }
    });

    searchInput.addEventListener('blur', function () {
        // Delay to allow dropdown click
        setTimeout(function () {
            dropdown.classList.remove('show');
        }, 200);
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _initAttendeeWidget);
} else {
    _initAttendeeWidget();
}
