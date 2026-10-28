// Core app JavaScript

(() => {
    document.addEventListener('click', (event) => {
        const navButton = event.target.closest('[data-toggle-nav]');
        if (navButton) {
            const collapsed = document.documentElement.classList.toggle('nav-collapsed');
            const isMobile = window.matchMedia('(max-width: 760px)').matches;
            navButton.setAttribute('aria-pressed', String(!collapsed));
            navButton.setAttribute('aria-expanded', String(!collapsed));
            navButton.setAttribute('aria-label', collapsed
                ? (isMobile ? 'Open navigation' : 'Expand navigation')
                : (isMobile ? 'Close navigation' : 'Collapse navigation'));
            navButton.querySelector('[data-nav-toggle-label]').textContent = collapsed
                ? (isMobile ? 'Menu' : 'Expand navigation')
                : (isMobile ? 'Close' : 'Collapse navigation');
            try {
                localStorage.setItem('ruachai-navigation', collapsed ? 'collapsed' : 'expanded');
            } catch (error) {
                // The navigation remains usable when browser storage is unavailable.
            }
            return;
        }

        const navigationLink = event.target.closest('#app-navigation a');
        if (navigationLink && window.matchMedia('(max-width: 760px)').matches) {
            document.documentElement.classList.add('nav-collapsed');
            const toggle = document.querySelector('[data-toggle-nav]');
            if (toggle) {
                toggle.setAttribute('aria-pressed', 'false');
                toggle.setAttribute('aria-expanded', 'false');
                toggle.setAttribute('aria-label', 'Open navigation');
                const label = toggle.querySelector('[data-nav-toggle-label]');
                if (label) label.textContent = 'Menu';
            }
            try {
                localStorage.setItem('ruachai-navigation', 'collapsed');
            } catch (error) {
                // Navigation remains usable when browser storage is unavailable.
            }
        }

        const themeButton = event.target.closest('[data-theme-toggle]');
        if (themeButton) {
            const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
            document.documentElement.dataset.theme = theme;
            const isDark = theme === 'dark';
            themeButton.setAttribute('aria-label', `Switch to ${isDark ? 'light' : 'dark'} mode`);
            themeButton.querySelector('[data-theme-label]').textContent = `${isDark ? 'Light' : 'Dark'} mode`;
            themeButton.querySelector('[data-theme-icon]').textContent = isDark ? '☀️' : '🌙';
            try {
                localStorage.setItem('ruachai-theme', theme);
            } catch (error) {
                // The selected theme remains active until the page is reloaded.
            }
            return;
        }

        const button = event.target.closest('[data-toggle-password]');
        if (!button) return;
        const fields = button.dataset.togglePassword
            .split(',')
            .map((id) => document.getElementById(id))
            .filter(Boolean);
        if (!fields.length) return;
        const reveal = fields.some((field) => field.type === 'password');
        fields.forEach((field) => { field.type = reveal ? 'text' : 'password'; });
        button.setAttribute('aria-pressed', String(reveal));
        button.setAttribute('aria-label', reveal ? 'Hide password' : 'Show password');
        button.title = reveal ? 'Hide password' : 'Show password';
        const icon = button.querySelector('.password-toggle-icon');
        if (icon) {
            icon.textContent = reveal ? '🙈' : '👁';
        } else {
            button.textContent = reveal ? '🙈' : '👁';
        }
    });

    const navButton = document.querySelector('[data-toggle-nav]');
    if (navButton) {
        const collapsed = document.documentElement.classList.contains('nav-collapsed');
        const isMobile = window.matchMedia('(max-width: 760px)').matches;
        navButton.setAttribute('aria-pressed', String(!collapsed));
        navButton.setAttribute('aria-expanded', String(!collapsed));
        navButton.setAttribute('aria-label', collapsed
            ? (isMobile ? 'Open navigation' : 'Expand navigation')
            : (isMobile ? 'Close navigation' : 'Collapse navigation'));
        navButton.querySelector('[data-nav-toggle-label]').textContent = collapsed
            ? (isMobile ? 'Menu' : 'Expand navigation')
            : (isMobile ? 'Close' : 'Collapse navigation');
    }

    const themeButton = document.querySelector('[data-theme-toggle]');
    if (themeButton) {
        const isDark = document.documentElement.dataset.theme === 'dark';
        themeButton.setAttribute('aria-label', `Switch to ${isDark ? 'light' : 'dark'} mode`);
        themeButton.querySelector('[data-theme-label]').textContent = `${isDark ? 'Light' : 'Dark'} mode`;
        themeButton.querySelector('[data-theme-icon]').textContent = isDark ? '☀️' : '🌙';
    }

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

// Beginner-friendly lesson aids: view mode, reading progress, and saved tasks.
(() => {
    const modeToggle = document.querySelector('[data-beginner-toggle]');
    if (modeToggle) {
        modeToggle.checked = document.documentElement.classList.contains('beginner-mode');
        modeToggle.addEventListener('change', () => {
            document.documentElement.classList.toggle('beginner-mode', modeToggle.checked);
            try {
                localStorage.setItem(
                    'ruachai-lesson-mode',
                    modeToggle.checked ? 'beginner' : 'full'
                );
            } catch (error) {
                // The chosen view still applies until the page is reloaded.
            }
        });
    }

    const progressBar = document.querySelector('[data-reading-progress]');
    if (progressBar) {
        const update = () => {
            const scrollable = document.documentElement.scrollHeight - window.innerHeight;
            const ratio = scrollable > 0 ? Math.min(1, window.scrollY / scrollable) : 0;
            progressBar.style.width = `${Math.round(ratio * 100)}%`;
        };
        update();
        window.addEventListener('scroll', update, { passive: true });
        window.addEventListener('resize', update);
    }

    const taskList = document.querySelector('[data-lesson-tasks]');
    if (taskList) {
        const key = `ruachai-tasks-${taskList.dataset.lessonId}`;
        let saved = [];
        try {
            const parsed = JSON.parse(localStorage.getItem(key) || '[]');
            if (Array.isArray(parsed)) saved = parsed.map(String);
        } catch (error) {
            saved = [];
        }
        const boxes = taskList.querySelectorAll('input[type="checkbox"]');
        boxes.forEach((box) => {
            if (saved.includes(box.dataset.taskIndex)) {
                box.checked = true;
                box.closest('li')?.classList.add('is-done');
            }
            box.addEventListener('change', () => {
                box.closest('li')?.classList.toggle('is-done', box.checked);
                const done = [...boxes]
                    .filter((item) => item.checked)
                    .map((item) => item.dataset.taskIndex);
                try {
                    localStorage.setItem(key, JSON.stringify(done));
                } catch (error) {
                    // Progress still shows for this visit.
                }
            });
        });
    }

    document.querySelectorAll('[data-open-practice]').forEach((link) => {
        link.addEventListener('click', (event) => {
            const launcher = document.getElementById('practice-launcher');
            if (!launcher) return;
            event.preventDefault();
            launcher.click();
            launcher.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
    });
})();

// Lesson video: privacy-enhanced, click-to-load YouTube player with progress.
(() => {
    const sections = document.querySelectorAll('[data-lesson-video]');
    if (!sections.length) return;

    const apiUrl = 'https://www.youtube.com/iframe_api';
    let apiPromise = null;

    function loadYouTubeApi() {
        if (window.YT && typeof window.YT.Player === 'function') {
            return Promise.resolve(window.YT);
        }
        if (apiPromise) return apiPromise;
        apiPromise = new Promise((resolve, reject) => {
            const previous = window.onYouTubeIframeAPIReady;
            window.onYouTubeIframeAPIReady = () => {
                if (typeof previous === 'function') previous();
                resolve(window.YT);
            };
            if (document.querySelector('script[data-youtube-api]')) return;
            const script = document.createElement('script');
            script.src = apiUrl;
            script.async = true;
            script.dataset.youtubeApi = 'true';
            script.onerror = () => reject(new Error('YouTube player unavailable'));
            document.head.appendChild(script);
        });
        return apiPromise;
    }

    function formatSeconds(value) {
        const total = Math.max(0, Math.round(Number(value) || 0));
        const hours = Math.floor(total / 3600);
        const minutes = Math.floor((total % 3600) / 60);
        const seconds = String(total % 60).padStart(2, '0');
        return hours
            ? `${hours}:${String(minutes).padStart(2, '0')}:${seconds}`
            : `${minutes}:${seconds}`;
    }

    function showFallback(frame, section, videoId) {
        const message = document.createElement('p');
        message.className = 'lesson-video-error';
        message.append('This video cannot be embedded here. ');
        const link = document.createElement('a');
        link.href = section.dataset.videoUrl
            || `https://www.youtube.com/watch?v=${videoId}`;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = 'Open it on YouTube ↗';
        message.append(link);
        frame.replaceChildren(message);
    }

    function setup(section) {
        const facade = section.querySelector('[data-video-play]');
        const frame = section.querySelector('.lesson-video-frame');
        const status = section.querySelector('[data-video-status]');
        const lessonId = section.dataset.lessonId;
        const videoId = section.dataset.videoId;
        const progressUrl = section.dataset.progressUrl;
        const clipStart = Number(section.dataset.videoStart || 0);
        const clipEnd = section.dataset.videoEnd
            ? Number(section.dataset.videoEnd) : null;
        const resumeAt = Number(section.dataset.resume || 0);
        const alreadyComplete = section.dataset.videoCompleted === 'true';
        let player = null;
        let timer = null;
        let lastReported = -1;
        let reportedComplete = alreadyComplete;
        let started = false;

        const setStatus = (text) => {
            if (status) status.textContent = text;
        };

        function report(position, duration, force = false) {
            if (!progressUrl || !lessonId) return;
            const rounded = Math.max(0, Math.round(Number(position) || 0));
            if (!force && Math.abs(rounded - lastReported) < 10) return;
            lastReported = rounded;
            fetch(progressUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                keepalive: true,
                body: JSON.stringify({
                    lesson_id: lessonId,
                    position_seconds: rounded,
                    duration_seconds: Math.max(0, Math.round(Number(duration) || 0)),
                }),
            }).then((response) => response.ok ? response.json() : null)
                .then((data) => {
                    if (!data) return;
                    if (data.completed) {
                        if (!reportedComplete) {
                            reportedComplete = true;
                            setStatus('Watched ✓');
                        }
                    } else if (!reportedComplete) {
                        setStatus(`Watching · ${formatSeconds(data.watched_seconds)} watched`);
                    }
                })
                .catch(() => {});
        }

        function beginPlayback() {
            if (started) return;
            started = true;
            if (facade) facade.remove();
            const mount = document.createElement('div');
            mount.id = `lesson-youtube-${videoId}`;
            frame.replaceChildren(mount);
            frame.classList.add('is-playing');
            loadYouTubeApi().then((YT) => {
                let startAt = alreadyComplete ? clipStart : Math.max(clipStart, resumeAt);
                if (clipEnd && startAt >= clipEnd - 5) startAt = clipStart;
                player = new YT.Player(mount.id, {
                    videoId,
                    host: 'https://www.youtube-nocookie.com',
                    playerVars: {
                        rel: 0,
                        playsinline: 1,
                        enablejsapi: 1,
                        origin: window.location.origin,
                        ...(startAt > 0 ? { start: Math.floor(startAt) } : {}),
                        ...(clipEnd ? { end: Math.floor(clipEnd) } : {}),
                    },
                    events: {
                        onReady: (event) => {
                            if (startAt > 0) event.target.seekTo(startAt, true);
                            event.target.playVideo();
                        },
                        onStateChange: (event) => {
                            const state = event.data;
                            if (state === YT.PlayerState.PLAYING) {
                                if (!reportedComplete) setStatus('Watching…');
                                if (!timer) {
                                    timer = window.setInterval(() => {
                                        if (player && typeof player.getCurrentTime === 'function') {
                                            report(player.getCurrentTime(), player.getDuration());
                                        }
                                    }, 10000);
                                }
                            }
                            if (state === YT.PlayerState.PAUSED) {
                                if (timer) { window.clearInterval(timer); timer = null; }
                                if (player && typeof player.getCurrentTime === 'function') {
                                    report(player.getCurrentTime(), player.getDuration(), true);
                                }
                            }
                            if (state === YT.PlayerState.ENDED) {
                                if (timer) { window.clearInterval(timer); timer = null; }
                                const duration = player && player.getDuration
                                    ? player.getDuration() : 0;
                                report(clipEnd || duration, duration, true);
                                setStatus('Watched ✓');
                                reportedComplete = true;
                            }
                        },
                        onError: () => {
                            if (timer) { window.clearInterval(timer); timer = null; }
                            showFallback(frame, section, videoId);
                            setStatus('Video unavailable here');
                        },
                    },
                });
            }).catch(() => {
                showFallback(frame, section, videoId);
                setStatus('Video unavailable here');
            });
        }

        if (facade) facade.addEventListener('click', beginPlayback);

        const flush = () => {
            if (player && typeof player.getCurrentTime === 'function') {
                report(player.getCurrentTime(), player.getDuration(), true);
            }
        };
        window.addEventListener('pagehide', flush);
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') flush();
        });
    }

    sections.forEach(setup);
})();

// Format time
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
}
