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
    try {
        const examDate = new Date(assessmentDate + ' 09:00:00').getTime();
        const now = new Date().getTime();
        const distance = examDate - now;
        
        if (distance > 0) {
            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const elem = document.getElementById('countdown-timer');
            if (elem) {
                elem.innerText = days + ' Days';
            }
        } else {
            const elem = document.getElementById('countdown-timer');
            if (elem) {
                elem.innerText = 'Today!';
            }
        }
    } catch (e) {
        console.error('Countdown error:', e);
    }
}

// Format time
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
}
