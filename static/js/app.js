// Core app JavaScript

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
