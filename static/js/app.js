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

// Format time
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
}
