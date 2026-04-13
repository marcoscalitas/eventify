let currentPage = 1;

document.addEventListener('DOMContentLoaded', () => {
    loadEvents();
    document.getElementById('searchInput').addEventListener('input', debounce(() => { currentPage = 1; loadEvents(); }, 300));
    document.getElementById('categoryFilter').addEventListener('change', () => { currentPage = 1; loadEvents(); });
});

function debounce(fn, delay) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

const SKELETON_COUNT = 6;

function renderSkeletons() {
    return Array.from({ length: SKELETON_COUNT }, () => `
        <div class="skeleton">
            <div class="skeleton__image"></div>
            <div class="skeleton__body">
                <div class="skeleton__line skeleton__line--title"></div>
                <div class="skeleton__line skeleton__line--medium"></div>
                <div class="skeleton__line skeleton__line--short"></div>
                <div class="skeleton__line skeleton__line--full"></div>
            </div>
        </div>
    `).join('');
}

function loadEvents() {
    const grid = document.getElementById('eventsGrid');
    grid.innerHTML = renderSkeletons();

    const search = document.getElementById('searchInput').value;
    const category = document.getElementById('categoryFilter').value;
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (category) params.append('category', category);
    params.append('page', currentPage);

    safeFetch(`/api/events?${params}`)
        .then(data => {
            const grid = document.getElementById('eventsGrid');
            if (data.events.length === 0) {
                grid.innerHTML = '<p class="events-grid__empty">No events found.</p>';
                document.getElementById('pagination').innerHTML = '';
                return;
            }
            grid.innerHTML = data.events.map(event => `
                <a href="/event/${event.id}" class="event-card">
                    <div class="event-card__image" style="background-image: url('${escapeHtml(event.image || '')}')">
                        ${event.category ? `<span class="event-card__category">${escapeHtml(event.category)}</span>` : ''}
                        ${event.average_rating ? `<span class="event-card__rating">★ ${event.average_rating}</span>` : ''}
                    </div>
                    <div class="event-card__body">
                        <h3>${escapeHtml(event.title)}</h3>
                        <p class="event-card__meta">📍 ${escapeHtml(event.location)}</p>
                        <p class="event-card__meta">📅 ${escapeHtml(event.date)} at ${escapeHtml(event.time)}</p>
                        <p class="event-card__description">${escapeHtml(event.description)}</p>
                        <div class="event-card__footer">
                            <span class="event-card__spots ${event.spots_left === 0 ? 'event-card__spots--full' : ''}">
                                ${event.spots_left > 0 ? event.spots_left + ' spots left' : 'Fully booked'}
                            </span>
                            <span class="event-card__organizer">by ${escapeHtml(event.organizer)}</span>
                        </div>
                    </div>
                </a>
            `).join('');

            renderPagination(data.page, data.total_pages);
        })
        .catch(() => {
            document.getElementById('eventsGrid').innerHTML = '<p class="events-grid__empty">Failed to load events.</p>';
        });
}

function renderPagination(page, totalPages) {
    const el = document.getElementById('pagination');
    if (totalPages <= 1) { el.innerHTML = ''; return; }
    let html = '';
    if (page > 1) html += `<button onclick="goToPage(${page - 1})">← Prev</button>`;
    html += `<span class="pagination__info">Page ${page} of ${totalPages}</span>`;
    if (page < totalPages) html += `<button onclick="goToPage(${page + 1})">Next →</button>`;
    el.innerHTML = html;
}

function goToPage(page) {
    currentPage = page;
    loadEvents();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
