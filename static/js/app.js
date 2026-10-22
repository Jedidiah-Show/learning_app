// Core app JavaScript

(() => {
    document.addEventListener('click', (event) => {
        const button = event.target.closest('[data-toggle-password]');
        if (!button) return;
        const fields = button.dataset.togglePassword
            .split(',')
            .map((id) => document.getElementById(id))
            .filter(Boolean);
        if (!fields.length) return;
        const reveal = fields.some((field) => field.type === 'password');
        fields.forEach((field) => { field.type = reveal ? 'text' : 'password'; });
        button.textContent = reveal ? 'Hide' : 'Show';
        button.setAttribute('aria-pressed', String(reveal));
    });

    const token = document.querySelector('meta[name="csrf-token"]')?.content;
    const nativeFetch = window.fetch.bind(window);
    window.fetch = (input, init = {}) => {
        const method = (init.method || input?.method || 'GET').toUpperCase();
        const url = new URL(typeof input === 'string' ? input : input.url, window.location.href);
        if (url.origin === window.location.origin) {
            const headers = new Headers(init.headers || (input instanceof Request ? input.headers : undefined));
            if (token && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
                headers.set('X-CSRF-Token', token);
            }
            const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            if (timeZone) headers.set('X-Timezone', timeZone);
            init = {...init, headers};
        }
        return nativeFetch(input, init);
    };
})();

function updateCountdown(assessmentDate) {
    const elem = document.getElementById('countdown-timer');
    if (!elem) return;
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(assessmentDate);
    if (!match) {
        elem.textContent = 'Date unavailable';
        return;
    }
    const [, year, month, day] = match;
    const examDate = new Date(Number(year), Number(month) - 1, Number(day), 9);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const examDay = new Date(Number(year), Number(month) - 1, Number(day));
    if (examDay < today || (examDay.getTime() === today.getTime() && now >= examDate)) {
        elem.textContent = 'Past due';
        return;
    }
    if (examDay.getTime() === today.getTime()) {
        elem.textContent = 'Today!';
        return;
    }
    elem.textContent = `${Math.ceil((examDay - today) / 86400000)} Days`;
}

// Format time
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
}
