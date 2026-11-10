import {defaultKeymap, indentWithTab} from '@codemirror/commands';
import {python} from '@codemirror/lang-python';
import {EditorState} from '@codemirror/state';
import {oneDark} from '@codemirror/theme-one-dark';
import {EditorView, keymap, lineNumbers} from '@codemirror/view';

const root = document.querySelector('[data-arena-workspace]');
if (root) {
    const loadUrl = root.dataset.loadUrl;
    const saveUrl = root.dataset.saveUrl;
    const editorialUrl = root.dataset.editorialUrl;
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    const editorHost = document.getElementById('arena-editor');
    const saveStatus = document.getElementById('arena-save-status');
    const output = document.getElementById('arena-output');
    const runButton = document.getElementById('arena-run');
    const resetButton = document.getElementById('arena-reset');
    const revealButton = document.getElementById('arena-reveal');
    const editorialPanel = document.getElementById('arena-editorial');
    const editorialCode = document.getElementById('arena-editorial-code');
    const editorialProse = document.getElementById('arena-editorial-prose');
    const iframe = document.getElementById('arena-sandbox');

    let problem = null;
    let editor;
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

    const setSaveStatus = (message, state = '') => {
        saveStatus.textContent = message;
        saveStatus.dataset.state = state;
    };

    const setOutput = (message, state = 'idle') => {
        output.textContent = message;
        output.dataset.state = state;
    };

    const currentSource = () => editor?.state.doc.toString() ?? '';

    const setEditorSource = (source) => {
        switching = true;
        editor.dispatch({
            changes: {from: 0, to: editor.state.doc.length, insert: source},
        });
        switching = false;
    };

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
        setOutput('Running public checks in the browser…', 'running');
        iframe.contentWindow.postMessage({
            type: 'run',
            runId,
            code: `${currentSource()}\n\n${problem.browser_checks}`,
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

    editor = new EditorView({
        state: EditorState.create({
            doc: '',
            extensions: [
                lineNumbers(),
                python(),
                oneDark,
                keymap.of([
                    {key: 'Mod-Enter', run: () => { void saveWorkspace().then(runChecks); return true; }},
                    {key: 'Mod-s', run: () => { void saveWorkspace(); return true; }},
                    ...defaultKeymap,
                    indentWithTab,
                ]),
                EditorView.lineWrapping,
                EditorView.updateListener.of((update) => {
                    if (update.docChanged && !switching) queueSave();
                }),
            ],
        }),
        parent: editorHost,
    });

    runButton.addEventListener('click', () => { void saveWorkspace().then(runChecks); });
    resetButton.addEventListener('click', () => {
        if (!problem) return;
        if (currentSource() !== problem.starter_code && !window.confirm('Discard your edits and restore the starter code?')) return;
        setEditorSource(problem.starter_code);
        queueSave();
        setOutput('Starter code restored.', 'idle');
    });
    revealButton.addEventListener('click', () => { void revealEditorial(); });
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
