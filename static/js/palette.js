// Command palette: ⌘/Ctrl+K opens a searchable jump-list over the same
// catalog the /search page uses. Keyboard-first: arrows move through the
// results, Enter opens, Esc closes, and focus returns to the page after.
(() => {
    const root = document.getElementById('command-palette');
    if (!root) return;

    const input = document.getElementById('palette-input');
    const list = document.getElementById('palette-results');
    const status = document.getElementById('palette-status');

    const QUICK_ACTIONS = [
        {icon: '🧠', title: 'Review center', meta: 'Spaced review queue', url: '/review'},
        {icon: '🎯', title: 'Quizzes', meta: 'Lesson and module quizzes', url: '/quizzes'},
        {icon: '🏟️', title: 'Practice Arena', meta: 'Solve problems in the sandbox', url: '/arena/'},
        {icon: '🧩', title: 'Projects', meta: 'Module projects and learning plan', url: '/projects'},
        {icon: '🛂', title: 'Skill Passport', meta: 'Evidence-based progress', url: '/passport'},
        {icon: '⚙️', title: 'Settings', meta: 'Model tier, tracking, calendar', url: '/settings'},
        {icon: '🛠️', title: 'Tech Support & Ideas', meta: 'Report a bug or suggest a feature', url: '/support'},
    ];

    let debounce = null;
    let requestSeq = 0;
    let lastFocused = null;

    const setStatus = (message) => {
        if (status) status.textContent = message;
    };

    const open = () => {
        lastFocused = document.activeElement;
        root.hidden = false;
        document.body.classList.add('palette-open');
        input.value = '';
        renderItems(QUICK_ACTIONS, 'Quick actions');
        setStatus('Type to search lessons, modules, and destinations.');
        // Defer so the element is visible before focusing on some browsers.
        window.setTimeout(() => input.focus(), 0);
    };

    const close = () => {
        root.hidden = true;
        document.body.classList.remove('palette-open');
        setStatus('Type to search · ↑↓ navigate · Enter opens · Esc closes');
        if (lastFocused && typeof lastFocused.focus === 'function') lastFocused.focus();
    };

    const itemButton = ({icon, title, meta, url}, index) => {
        const li = document.createElement('li');
        li.setAttribute('role', 'presentation');
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'palette-item';
        button.dataset.url = url;
        button.id = `palette-item-${index}`;
        const iconSpan = document.createElement('span');
        iconSpan.className = 'palette-item-icon';
        iconSpan.setAttribute('aria-hidden', 'true');
        iconSpan.textContent = icon || '📖';
        const body = document.createElement('span');
        body.className = 'palette-item-body';
        const titleSpan = document.createElement('span');
        titleSpan.className = 'palette-item-title';
        titleSpan.textContent = title;
        body.append(titleSpan);
        if (meta) {
            const metaSpan = document.createElement('span');
            metaSpan.className = 'palette-item-meta';
            metaSpan.textContent = meta;
            body.append(metaSpan);
        }
        button.append(iconSpan, body);
        button.addEventListener('click', () => { window.location.assign(url); });
        li.append(button);
        return li;
    };

    const renderItems = (rows, emptyMessage) => {
        list.replaceChildren();
        if (!rows.length) {
            const li = document.createElement('li');
            li.className = 'palette-empty';
            li.textContent = emptyMessage || 'Nothing matches that. Try a broader term.';
            list.append(li);
            return;
        }
        rows.forEach((row, index) => list.append(itemButton(row, index)));
    };

    const runSearch = async (query) => {
        const seq = ++requestSeq;
        setStatus('Searching…');
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=8`);
            const data = await response.json().catch(() => ({}));
            if (seq !== requestSeq || root.hidden) return;
            if (!response.ok) {
                renderItems([], data.error || 'Search is unavailable right now.');
                setStatus(data.error || 'Search is unavailable right now.');
                return;
            }
            const lessons = Array.isArray(data.results) ? data.results : [];
            renderItems(
                lessons.map((lesson) => ({
                    icon: lesson.source === 'ml' ? '📊' : '📖',
                    title: lesson.title,
                    meta: [lesson.badge || (lesson.module_number != null ? `Module ${lesson.module_number}` : null), lesson.ordinal != null ? `Lesson ${lesson.ordinal}` : null].filter(Boolean).join(' · '),
                    url: lesson.url,
                })),
                `No lessons match “${query}”.`,
            );
            setStatus(lessons.length ? `${lessons.length} match${lessons.length === 1 ? '' : 'es'}.` : `No lessons match “${query}”.`);
        } catch (error) {
            if (seq !== requestSeq || root.hidden) return;
            renderItems([], 'Search is unavailable. Check your connection.');
            setStatus('Search is unavailable. Check your connection.');
        }
    };

    input.addEventListener('input', () => {
        const query = input.value.trim();
        window.clearTimeout(debounce);
        if (query.length < 2) {
            requestSeq += 1; // cancel any in-flight search
            renderItems(QUICK_ACTIONS, '');
            setStatus('Type at least 2 characters to search lessons.');
            return;
        }
        debounce = window.setTimeout(() => { void runSearch(query); }, 150);
    });

    input.addEventListener('keydown', (event) => {
        const buttons = [...list.querySelectorAll('.palette-item')];
        const current = buttons.findIndex((button) => button === document.activeElement);
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault();
            const delta = event.key === 'ArrowDown' ? 1 : -1;
            const next = buttons.length ? (current === -1 ? (delta === 1 ? 0 : buttons.length - 1) : (current + delta + buttons.length) % buttons.length) : -1;
            if (next !== -1) buttons[next].focus();
        } else if (event.key === 'Enter' && current !== -1) {
            event.preventDefault();
            buttons[current].click();
        } else if (event.key === 'Escape') {
            event.preventDefault();
            close();
        }
    });

    root.addEventListener('mousedown', (event) => {
        if (event.target === root) close();
    });

    document.addEventListener('keydown', (event) => {
        const mod = event.metaKey || event.ctrlKey;
        if (mod && (event.key === 'k' || event.key === 'K')) {
            event.preventDefault();
            if (root.hidden) open(); else close();
        } else if (!root.hidden && event.key === 'Escape') {
            event.preventDefault();
            close();
        }
    });
})();
