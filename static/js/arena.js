import {createPythonEditor} from './python-editor.js';

const root = document.querySelector('[data-arena-workspace]');
if (root) {
    const loadUrl = root.dataset.loadUrl;
    const saveUrl = root.dataset.saveUrl;
    const submitUrl = root.dataset.submitUrl;
    const hintUrl = root.dataset.hintUrl;
    const editorialUrl = root.dataset.editorialUrl;
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    const editorHost = document.getElementById('arena-editor');
    const saveStatus = document.getElementById('arena-save-status');
    const output = document.getElementById('arena-output');
    const statusBar = document.getElementById('arena-statusbar');
    const statusPosition = document.getElementById('arena-statusbar-position');
    const runButton = document.getElementById('arena-run');
    const submitButton = document.getElementById('arena-submit');
    const customChecks = document.getElementById('arena-custom-checks');
    const hintOutput = document.getElementById('arena-hint-output');
    const themeButton = document.getElementById('arena-theme');
    const fullscreenButton = document.getElementById('arena-fullscreen');
    const resizeHandle = document.getElementById('arena-resize');
    const panels = document.getElementById('arena-panels');
    const resetButton = document.getElementById('arena-reset');
    const revealButton = document.getElementById('arena-reveal');
    const editorialPanel = document.getElementById('arena-editorial');
    const editorialCode = document.getElementById('arena-editorial-code');
    const editorialProse = document.getElementById('arena-editorial-prose');
    const iframe = document.getElementById('arena-sandbox');

    let problem = null;
    let editor;
    try {
        editor = createPythonEditor(editorHost, {
            theme: 'dark',
            onChange: (source) => {
                if (switching || source === savedSource) return;
                queueSave();
            },
            onCursorChange: (line, col) => {
                if (!statusPosition) return;
                statusPosition.textContent = `Ln ${line}, Col ${col}`;
            },
            runCommand: () => { void saveWorkspace().then(runChecks); },
            saveCommand: () => { void saveWorkspace(); },
        });
    } catch (e) {
        console.error('Failed to create editor', e);
        if (editorHost) {
            editorHost.innerHTML = `<div style="padding:12px;color:#f87171;">Failed to load code editor. Please refresh.<br><small>${String(e && e.message || e)}</small></div>`;
        }
    }
    let savedSource = '';
    let saveTimer = null;
    let savePromise = null;
    let switching = false;
    let runnerReady = false;
    let runnerStarted = false;
    let runnerLoadTimeout = null;
    let queuedRun = false;
    let activeRunId = null;
    let nextRunId = 0;
    let runTimeout = null;
    let lightTheme = false;

    const setSaveStatus = (message, state = '') => {
        saveStatus.textContent = message;
        saveStatus.dataset.state = state;
    };

    const setOutput = (message, state = 'idle') => {
        output.textContent = message;
        output.dataset.state = state;
    };

    const currentSource = () => {
        if (editor) {
            return editor.getSource();
        }
        return '';
    };

    const setEditorSource = (source) => {
        if (editor) {
            switching = true;
            editor.setSource(source);
        }
        switching = false;
    };

    themeButton.addEventListener('click', () => {
        if (!editor) return;
        lightTheme = !lightTheme;
        editor.setTheme(lightTheme ? 'light' : 'dark');
        themeButton.setAttribute('aria-pressed', String(lightTheme));
        themeButton.textContent = lightTheme ? 'Dark editor' : 'Light editor';
    });

    fullscreenButton.addEventListener('click', async () => {
        try {
            if (document.fullscreenElement === root) {
                await document.exitFullscreen();
            } else {
                await root.requestFullscreen();
            }
        } catch (error) {
            setOutput('Full-screen mode is unavailable in this browser.', 'error');
        }
    });
    document.addEventListener('fullscreenchange', () => {
        fullscreenButton.textContent = document.fullscreenElement === root
            ? 'Exit full screen'
            : 'Full screen';
    });

    let resizeStart = null;
    let paneLeftWidth = null;
    resizeHandle.addEventListener('pointerdown', (event) => {
        const bounds = panels.getBoundingClientRect();
        resizeStart = {
            pointerId: event.pointerId,
            pointerX: event.clientX,
            leftWidth: paneLeftWidth ?? (bounds.width - 48) / 2,
            width: bounds.width,
        };
        resizeHandle.setPointerCapture(event.pointerId);
    });
    resizeHandle.addEventListener('pointermove', (event) => {
        if (!resizeStart || resizeStart.pointerId !== event.pointerId) return;
        const gutter = 8;
        paneLeftWidth = Math.min(
            Math.max(resizeStart.leftWidth + event.clientX - resizeStart.pointerX, 280),
            resizeStart.width - gutter - 40 - 280,
        );
        panels.style.gridTemplateColumns = `minmax(280px, ${paneLeftWidth}px) ${gutter}px minmax(280px, 1fr)`;
        resizeHandle.setAttribute(
            'aria-valuenow',
            String(Math.round((paneLeftWidth / (resizeStart.width - gutter - 40)) * 100)),
        );
    });
    const stopResize = () => { resizeStart = null; };
    resizeHandle.addEventListener('pointerup', stopResize);
    resizeHandle.addEventListener('pointercancel', stopResize);
    resizeHandle.addEventListener('keydown', (event) => {
        if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
        event.preventDefault();
        const bounds = panels.getBoundingClientRect();
        paneLeftWidth = Math.min(
            Math.max((paneLeftWidth ?? (bounds.width - 48) / 2) + (event.key === 'ArrowRight' ? 24 : -24), 280),
            bounds.width - 336,
        );
        panels.style.gridTemplateColumns = `minmax(280px, ${paneLeftWidth}px) 8px minmax(280px, 1fr)`;
        resizeHandle.setAttribute(
            'aria-valuenow',
            String(Math.round((paneLeftWidth / (bounds.width - 48)) * 100)),
        );
    });

    const saveWorkspace = async () => {
        clearTimeout(saveTimer);
        if (savePromise) {
            const saved = await savePromise;
            if (!saved) return false;
            return currentSource() === savedSource ? true : saveWorkspace();
        }
        const source = currentSource();
        if (!problem || source === savedSource) return true;

        savePromise = (async () => {
            setSaveStatus('Saving…', 'saving');
            try {
                const response = await fetch(saveUrl, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken,
                    },
                    body: JSON.stringify({source}),
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) {
                    throw new Error(data.error || 'Could not save your work.');
                }
                savedSource = source;
                setSaveStatus('Saved', 'saved');
                if (currentSource() !== savedSource) queueSave();
                return true;
            } catch (error) {
                setSaveStatus(error.message || 'Could not save your work.', 'error');
                return false;
            } finally {
                savePromise = null;
            }
        })();
        return savePromise;
    };

    const queueSave = () => {
        clearTimeout(saveTimer);
        setSaveStatus('Unsaved changes', 'dirty');
        saveTimer = setTimeout(() => { void saveWorkspace(); }, 700);
    };

    const loadProblem = async () => {
        setSaveStatus('Loading saved work…', 'saving');
        try {
            const response = await fetch(loadUrl);
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Could not load this problem.');
            }
            problem = data.problem;
            savedSource = data.source;
            setEditorSource(data.source);
            setSaveStatus(data.updated_at ? 'Saved work loaded' : 'Starter code loaded', 'saved');
            runButton.disabled = !runnerReady;
            submitButton.disabled = false;
            if (editor) void editor.languageReady;
        } catch (error) {
            setSaveStatus(error.message || 'Could not load this problem.', 'error');
            setOutput('The problem could not be loaded. Reload the page to try again.', 'error');
        }
    };

    const startRunner = () => {
        if (runnerStarted) return;
        runnerStarted = true;
        setOutput('Loading the browser Python runtime…', 'loading');
        iframe.src = '/static/practice-sandbox.html';
        runnerLoadTimeout = setTimeout(() => {
            if (runnerReady) return;
            runnerStarted = false;
            queuedRun = false;
            runButton.disabled = false;
            iframe.src = 'about:blank';
            setOutput('The Python runtime did not respond. Check that your browser allows background workers, then reload.', 'error');
        }, 45000);
    };

    const runChecks = () => {
        if (!problem) return;
        if (!runnerReady) {
            queuedRun = true;
            runButton.disabled = true;
            startRunner();
            return;
        }
        const runId = ++nextRunId;
        activeRunId = runId;
        runButton.disabled = true;
        setOutput('Running your code and optional local checks in the browser…', 'running');
        iframe.contentWindow.postMessage({
            type: 'run',
            runId,
            code: `${currentSource()}\n\n${customChecks.value}`,
        }, '*');
        clearTimeout(runTimeout);
        runTimeout = setTimeout(() => {
            if (activeRunId !== runId) return;
            activeRunId = null;
            runButton.disabled = false;
            setOutput('Execution timed out. The browser worker was stopped; simplify the code and try again.', 'error');
            runnerReady = false;
            runnerStarted = false;
            iframe.src = 'about:blank';
        }, 10000);
    };

    const submitCode = async () => {
        if (!problem || !await saveWorkspace()) return;
        submitButton.disabled = true;
        runButton.disabled = true;
        setOutput('Submitting to the isolated server judge…', 'running');
        try {
            const response = await fetch(submitUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrfToken,
                },
                body: JSON.stringify({code: currentSource()}),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.error || 'Server judging is unavailable.');
            }
            let result = data;
            for (let attempt = 0; result.verdict === 'PENDING' || result.verdict === 'RUNNING'; attempt += 1) {
                if (attempt >= 60) throw new Error('The judge is taking longer than expected. Check your submission status shortly.');
                await new Promise((resolve) => setTimeout(resolve, 1000));
                const statusResponse = await fetch(`/arena/api/submissions/${encodeURIComponent(data.submission_id)}`);
                result = await statusResponse.json();
                if (!statusResponse.ok) throw new Error(result.error || 'Could not load submission status.');
            }
            const verdict = result.verdict || 'INTERNAL_ERROR';
            setOutput(
                `${verdict.replaceAll('_', ' ')} · ${result.tests_passed}/${result.total_tests} checks · ${result.execution_time_ms} ms`,
                verdict === 'ACCEPTED' ? 'done' : 'error',
            );
            const status = document.getElementById('problem-status');
            if (verdict === 'ACCEPTED') {
                status.textContent = 'Demonstrated';
                status.dataset.verdict = verdict;
            }
        } catch (error) {
            setOutput(error.message || 'Server judging is unavailable.', 'error');
        } finally {
            submitButton.disabled = false;
            runButton.disabled = !runnerReady;
        }
    };

    const revealEditorial = async () => {
        if (!problem) return;
        if (!window.confirm('Reveal the worked solution? Try to save your own attempt first; the server only reveals this after an attempt exists.')) return;
        revealButton.disabled = true;
        try {
            const response = await fetch(editorialUrl);
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.error || 'The worked solution is not available yet.');
            }
            editorialCode.textContent = data.solution_code || '(No reference code supplied.)';
            editorialProse.textContent = data.editorial || '';
            editorialPanel.classList.remove('hidden');
            editorialPanel.scrollIntoView({block: 'nearest'});
        } catch (error) {
            setOutput(error.message, 'error');
        } finally {
            revealButton.disabled = false;
        }
    };

    runButton.addEventListener('click', () => { void saveWorkspace().then(runChecks); });
    submitButton.addEventListener('click', () => { void submitCode(); });
    resetButton.addEventListener('click', () => {
        if (!problem) return;
        if (currentSource() !== problem.starter_code && !window.confirm('Discard your edits and restore the starter code?')) return;
        setEditorSource(problem.starter_code);
        queueSave();
        setOutput('Starter code restored.', 'idle');
    });
    revealButton.addEventListener('click', () => { void revealEditorial(); });
    document.querySelectorAll('[data-arena-hint]').forEach((button) => {
        button.addEventListener('click', async () => {
            button.disabled = true;
            hintOutput.textContent = 'Preparing hint…';
            try {
                const stage = Number(button.dataset.stage);
                const response = await fetch(
                    `${hintUrl}?stage=${encodeURIComponent(stage)}`,
                );
                const data = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(data.error || 'Hint is unavailable.');
                hintOutput.textContent = data.hint;
            } catch (error) {
                hintOutput.textContent = error.message || 'Hint is unavailable.';
            } finally {
                button.disabled = false;
            }
        });
    });
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') void saveWorkspace();
    });

    window.addEventListener('message', (event) => {
        if (
            event.source !== iframe.contentWindow
            || event.origin !== 'null'
            || !event.data
        ) return;
        if (event.data.type === 'ready') {
            clearTimeout(runnerLoadTimeout);
            runnerReady = true;
            runButton.disabled = false;
            if (!queuedRun) setOutput('Python runtime ready. Run the public checks when you are ready.', 'idle');
            if (queuedRun) {
                queuedRun = false;
                runChecks();
            }
            return;
        }
        if (event.data.type === 'error' && event.data.runId == null) {
            clearTimeout(runnerLoadTimeout);
            runnerReady = false;
            queuedRun = false;
            runnerStarted = false;
            iframe.src = 'about:blank';
            runButton.disabled = false;
            setOutput(event.data.text || 'The Python runtime failed to load.', 'error');
            return;
        }
        if (event.data.type === 'run-started') {
            setOutput('Running public checks…', 'running');
            return;
        }
        if (event.data.runId !== activeRunId) return;
        if (event.data.type === 'output') {
            output.textContent = `${output.textContent}${event.data.text}`.slice(0, 12000);
        } else if (
            event.data.type === 'done'
            || event.data.type === 'error'
            || event.data.type === 'timeout'
        ) {
            clearTimeout(runTimeout);
            activeRunId = null;
            runButton.disabled = false;
            setOutput(event.data.text, event.data.type === 'done' ? 'done' : 'error');
        }
    });

    void loadProblem();
}
