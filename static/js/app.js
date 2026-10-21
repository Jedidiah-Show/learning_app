// Core app JavaScript

(() => {
    const token = document.querySelector('meta[name="csrf-token"]')?.content;
    const nativeFetch = window.fetch.bind(window);
    window.fetch = (input, init = {}) => {
        const method = (init.method || input?.method || 'GET').toUpperCase();
        const url = new URL(typeof input === 'string' ? input : input.url, window.location.href);
        if (token && url.origin === window.location.origin &&
            ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
            const headers = new Headers(init.headers || (input instanceof Request ? input.headers : undefined));
            headers.set('X-CSRF-Token', token);
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
