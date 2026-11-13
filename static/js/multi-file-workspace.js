import {createPythonEditor} from './python-editor.js';

const script = document.currentScript || document.querySelector('script[data-project-key]');
const projectKey = script?.dataset.projectKey || '';
const apiUrl = script?.dataset.apiUrl || '';

const saveStatus = document.getElementById('workspace-save-status');
const fileList = document.getElementById('workspace-file-list');
const fileError = document.getElementById('workspace-file-error');
const output = document.getElementById('workspace-output');
const statusFile = document.getElementById('workspace-statusbar-file');
const statusPosition = document.getElementById('workspace-statusbar-position');
const runButton = document.getElementById('workspace-run');
const checksButton = document.getElementById('workspace-checks');
const resetButton = document.getElementById('workspace-reset');
const clearOutputButton = document.getElementById('workspace-clear-output');
const newFileForm = document.getElementById('workspace-new-file-form');
const newFileInput = document.getElementById('workspace-new-file-name');
const iframe = document.getElementById('workspace-sandbox');
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

const setSaveStatus = (message, state = '') => {
    if (!saveStatus) return;
    saveStatus.textContent = message;
    saveStatus.dataset.state = state;
};
const showFileError = (message) => {
    if (!fileError) return;
    fileError.textContent = message || '';
    fileError.classList.toggle('hidden', !message);
};
const appendOutput = (message) => {
    if (!output) return;
    output.textContent = `${output.textContent}${String(message)}`.slice(0, 20000);
    output.scrollTop = output.scrollHeight;
};
const setOutput = (message) => {
    if (!output) return;
    output.textContent = String(message);
    output.scrollTop = output.scrollHeight;
};

const isSafePath = (path) => {
    if (typeof path !== 'string') return false;
    const trimmed = path.trim();
    if (!trimmed || trimmed.length > 200 || trimmed.startsWith('/') || trimmed.includes('\\') || trimmed.includes('\0')) return false;
    const segments = trimmed.split('/');
    if (segments.length > 8) return false;
    return segments.every((segment) => segment && segment !== '.' && segment !== '..' && /^[A-Za-z0-9_.-]+$/.test(segment));
};

let files = {};
let activePath = null;
let seeded = false;
let dirty = false;
let savedSnapshot = '{}';
let saveTimer = null;
let activeRunId = null;
let runnerReady = false;
let nextRunId = 0;

let editor = null;
try {
    editor = createPythonEditor(document.getElementById('workspace-editor'), {
        theme: 'dark',
        onChange: (source) => {
            if (activePath === null) return;
            files[activePath] = source;
            dirty = true;
            setSaveStatus('Unsaved changes', 'dirty');
            clearTimeout(saveTimer);
            saveTimer = setTimeout(() => { void saveWorkspace(); }, 2500);
        },
        onCursorChange: (line, col) => {
            if (statusPosition) statusPosition.textContent = `Ln ${line}, Col ${col}`;
        },
        runCommand: () => { void runProject('run'); },
        saveCommand: () => { void saveWorkspace(); },
    });
} catch (error) {
    console.error('Failed to create editor', error);
    const host = document.getElementById('workspace-editor');
    if (host) {
        host.innerHTML = '<div style="padding:12px;color:#f87171">Failed to load code editor. Please refresh.</div>';
    }
}

const firstPythonPath = (mapping) => {
    const paths = Object.keys(mapping).sort();
    for (const preferred of ['main.py', 'src/main.py']) {
        if (preferred in mapping) return preferred;
    }
    return paths.find((path) => path.endsWith('.py')) || paths[0] || null;
};

const renderFileList = () => {
    if (!fileList) return;
    fileList.innerHTML = '';
    const paths = Object.keys(files).sort();
    if (paths.length === 0) {
        fileList.innerHTML = '<li class="px-2 py-2 text-xs text-slate-500">No files yet — add one above.</li>';
        return;
    }
    for (const path of paths) {
        const item = document.createElement('li');
        item.className = 'flex items-center gap-1';
        const activate = document.createElement('button');
        activate.type = 'button';
        activate.dataset.filePath = path;
        activate.className = `grow rounded-lg px-2 py-1.5 text-left text-xs font-mono ${
            path === activePath
                ? 'bg-indigo-100 text-indigo-900 dark:bg-indigo-950 dark:text-indigo-200'
                : 'text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800'
        }`;
        activate.textContent = path;
        activate.addEventListener('click', () => { switchTo(path); });
        const rename = document.createElement('button');
        rename.type = 'button';
        rename.textContent = '✎';
        rename.title = 'Rename file';
        rename.className = 'rounded px-1.5 py-1 text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200';
        rename.addEventListener('click', () => {
            const next = window.prompt('Rename file to:', path);
            if (next === null) return;
            void renameFile(path, next.trim());
        });
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.textContent = '×';
        remove.title = 'Delete file';
        remove.className = 'rounded px-1.5 py-1 text-xs text-slate-400 hover:bg-rose-50 hover:text-rose-700 dark:hover:bg-rose-950';
        remove.addEventListener('click', () => {
            if (window.confirm(`Delete ${path}?`)) void deleteFile(path);
        });
        item.append(activate, rename, remove);
        fileList.append(item);
    }
};

const switchTo = (path) => {
    if (!(path in files)) return;
    activePath = path;
    if (editor) editor.setSource(files[path]);
    if (statusFile) statusFile.textContent = path;
    renderFileList();
};

const renameFile = async (from, to) => {
    if (!isSafePath(to)) {
        showFileError('Use a safe path like src/module.py (letters, digits, . _ - and /).');
        return;
    }
    if (to === from) return;
    if (to in files) {
        showFileError(`A file named ${to} already exists.`);
        return;
    }
    showFileError('');
    files[to] = files[from];
    delete files[from];
    if (activePath === from) {
        activePath = to;
        if (statusFile) statusFile.textContent = to;
    }
    dirty = true;
    renderFileList();
    await saveWorkspace();
};

const deleteFile = async (path) => {
    delete files[path];
    if (activePath === path) {
        const next = firstPythonPath(files);
        activePath = next;
        if (editor) editor.setSource(files[next] || '');
        if (statusFile) statusFile.textContent = next || '—';
    }
    dirty = true;
    renderFileList();
    await saveWorkspace();
};

const saveWorkspace = async () => {
    if (!dirty) return true;
    setSaveStatus('Saving…', 'saving');
    try {
        const response = await fetch(apiUrl, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken,
                Accept: 'application/json',
            },
            body: JSON.stringify({files}),
        });
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            setSaveStatus(data.error || 'Could not save the workspace.', 'error');
            return false;
        }
        const data = await response.json();
        files = data.files || files;
        savedSnapshot = JSON.stringify(files);
        dirty = false;
        seeded = false;
        setSaveStatus('Saved', 'saved');
        return true;
    } catch (error) {
        setSaveStatus('Network error — your draft stays in this browser.', 'error');
        return false;
    }
};

const loadWorkspace = async () => {
    try {
        const response = await fetch(apiUrl, {headers: {Accept: 'application/json'}});
        if (!response.ok) {
            setSaveStatus('Could not load workspace.', 'error');
            return;
        }
        const data = await response.json();
        files = data.files || {};
        seeded = Boolean(data.seeded);
        savedSnapshot = JSON.stringify(files);
        dirty = false;
        setSaveStatus(seeded ? 'Starter kit loaded' : 'Saved', seeded ? 'seeded' : 'saved');
        const openPath = firstPythonPath(files);
        activePath = openPath;
        if (openPath && editor) editor.setSource(files[openPath]);
        if (statusFile) statusFile.textContent = openPath || '—';
        renderFileList();
        runButton.disabled = false;
    } catch (error) {
        setSaveStatus('Network error — could not load the workspace.', 'error');
    }
};

const runProject = async (mode) => {
    const entry = firstPythonPath(files);
    if (!entry) {
        setOutput('There is no Python file to run.');
        return;
    }
    activeRunId = ++nextRunId;
    runButton.disabled = true;
    checksButton.disabled = true;
    setOutput(mode === 'checks' ? 'Running checks in tests/…' : `Running ${entry}…`);
    iframe.contentWindow.postMessage({
        type: mode === 'checks' ? 'checks' : 'run',
        runId: activeRunId,
        files,
        entry,
    }, '*');
};

newFileForm?.addEventListener('submit', (event) => {
    event.preventDefault();
    const name = newFileInput.value.trim();
    if (!isSafePath(name)) {
        showFileError('Use a safe path like src/module.py (letters, digits, . _ - and /).');
        return;
    }
    showFileError('');
    files[name] = '';
    activePath = name;
    if (editor) editor.setSource('');
    if (statusFile) statusFile.textContent = name;
    dirty = true;
    newFileInput.value = '';
    renderFileList();
    void saveWorkspace();
});

iframe.addEventListener('load', () => {
    activeRunId = null;
    runnerReady = false;
});
iframe.src = '/static/workspace-sandbox.html';

window.addEventListener('message', (event) => {
    if (event.source !== iframe.contentWindow) return;
    const data = event.data;
    if (!data || (data.type !== 'output' && data.type !== 'done' && data.type !== 'error'
        && data.type !== 'timeout' && data.type !== 'run-started' && data.type !== 'ready')) return;
    if (data.runId !== undefined && activeRunId !== null && data.runId !== activeRunId) return;
    if (data.type === 'ready') {
        runnerReady = true;
        setSaveStatus(savedSnapshot !== '{}' ? (seeded ? 'Starter kit loaded' : 'Saved') : 'Saved', 'saved');
        return;
    }
    if (data.type === 'output') {
        appendOutput(data.text);
        return;
    }
    if (data.type === 'run-started') return;
    runButton.disabled = false;
    checksButton.disabled = false;
    activeRunId = null;
    appendOutput(data.type === 'done' ? `\n${data.text}\n` : `\n${data.text}\n`);
});

runButton?.addEventListener('click', () => { void runProject('run'); });
checksButton?.addEventListener('click', () => { void runProject('checks'); });
resetButton?.addEventListener('click', async () => {
    if (!window.confirm('Reset the workspace to the starter kit? Your edits will be discarded.')) return;
    try {
        const response = await fetch(`${apiUrl}/reset`, {
            method: 'POST',
            headers: {'X-CSRF-Token': csrfToken, Accept: 'application/json'},
        });
        if (!response.ok) {
            const res = await response.json().catch(() => ({}));
            setSaveStatus(res.error || 'Could not reset the workspace.', 'error');
            return;
        }
        const data = await response.json();
        files = data.files || {};
        savedSnapshot = JSON.stringify(files);
        dirty = false;
        const openPath = firstPythonPath(files);
        activePath = openPath;
        if (editor) editor.setSource(openPath ? files[openPath] : '');
        if (statusFile) statusFile.textContent = openPath || '—';
        setSaveStatus('Starter kit loaded', 'saved');
        renderFileList();
    } catch (error) {
        setSaveStatus('Network error — could not reset.', 'error');
    }
});
clearOutputButton?.addEventListener('click', () => { setOutput(''); });
window.addEventListener('beforeunload', (event) => {
    if (!dirty) return;
    event.preventDefault();
    event.returnValue = '';
});

void loadWorkspace();
