import {defaultKeymap, indentWithTab} from '@codemirror/commands';
import {python} from '@codemirror/lang-python';
import {EditorState} from '@codemirror/state';
import {oneDark} from '@codemirror/theme-one-dark';
import {EditorView, keymap, lineNumbers} from '@codemirror/view';

const root = document.querySelector('[data-practice-workspace]');
if (root) {
    const lessonId = root.dataset.lessonId;
    const exerciseList = JSON.parse(
        document.getElementById('practice-exercises').textContent,
    );
    const launcher = document.getElementById('practice-launcher');
    const panel = document.getElementById('practice-panel');
    const editorHost = document.getElementById('practice-editor');
    const selector = document.getElementById('practice-exercise-select');
    const instructions = document.getElementById('practice-instructions');
    const status = document.getElementById('practice-save-status');
    const output = document.getElementById('practice-output');
    const runButton = document.getElementById('practice-run');
    const resetButton = document.getElementById('practice-reset');
    const iframe = document.getElementById('practice-sandbox');
    let selectedExercise = null;
    let savedSource = '';
    let saveTimer = null;
    let savePromise = null;
    let editor;
    let switching = false;
    let runnerReady = false;
    let activeRunId = null;
    let runTimeout = null;
    let nextRunId = 0;
    let queuedRun = false;
    let runnerStarted = false;
    let runnerLoadTimeout = null;

    const workspaceUrl = (exercise) =>
        `/api/lessons/practice/${encodeURIComponent(lessonId)}/${encodeURIComponent(exercise.id)}`;

    const setStatus = (message, state = '') => {
        status.textContent = message;
        status.dataset.state = state;
    };

    const currentSource = () => editor?.state.doc.toString() ?? '';

    const saveWorkspace = async () => {
        clearTimeout(saveTimer);
        if (savePromise) {
            const saved = await savePromise;
            if (!saved) return false;
            return currentSource() === savedSource ? true : saveWorkspace();
        }
        const source = currentSource();
        if (!selectedExercise || source === savedSource) return true;

        savePromise = (async () => {
            setStatus('Saving…', 'saving');
            try {
                const response = await fetch(workspaceUrl(selectedExercise), {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({source}),
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Could not save your work.');
                savedSource = source;
                setStatus('Saved', 'saved');
                if (currentSource() !== savedSource) queueSave();
                return true;
            } catch (error) {
                setStatus(error.message || 'Could not save your work.', 'error');
                return false;
            } finally {
                savePromise = null;
            }
        })();
        return savePromise;
    };

    const queueSave = () => {
        clearTimeout(saveTimer);
        setStatus('Unsaved changes', 'dirty');
        saveTimer = setTimeout(() => { void saveWorkspace(); }, 700);
    };

    const setEditorSource = (source) => {
        editor.dispatch({
            changes: {from: 0, to: editor.state.doc.length, insert: source},
        });
    };

    const loadExercise = async (exercise) => {
        const previousExercise = selectedExercise;
        switching = true;
        selectedExercise = exercise;
        document.getElementById('practice-task-title').textContent = exercise.title;
        instructions.textContent = exercise.instructions;
        output.textContent = 'Run your code to see output and checks.';
        runButton.disabled = true;
        setStatus('Loading saved work…', 'saving');
        try {
            const response = await fetch(workspaceUrl(exercise));
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Could not load this exercise.');
            savedSource = data.source;
            setEditorSource(data.source);
            setStatus(data.updated_at ? 'Saved work loaded' : 'Starter code loaded', 'saved');
        } catch (error) {
            if (previousExercise) {
                selectedExercise = previousExercise;
                selector.value = previousExercise.id;
                document.getElementById('practice-task-title').textContent = previousExercise.title;
                instructions.textContent = previousExercise.instructions;
            }
            setStatus(error.message || 'Could not load this exercise.', 'error');
        } finally {
            switching = false;
            runButton.disabled = !runnerReady;
        }
    };

    const resizeEditor = () => requestAnimationFrame(() => editor?.requestMeasure());

    const openPanel = () => {
        panel.hidden = false;
        panel.classList.remove('is-collapsed');
        launcher.hidden = true;
        document.getElementById('practice-collapse').setAttribute('aria-expanded', 'true');
        resizeEditor();
    };

    const closePanel = async () => {
        if (!(await saveWorkspace())) return;
        panel.hidden = true;
        panel.classList.remove('is-maximized', 'is-collapsed');
        launcher.hidden = false;
    };

    const setRunOutput = (text, isError = false) => {
        output.textContent = text;
        output.dataset.state = isError ? 'error' : 'output';
    };

    const startRunner = () => {
        if (!runnerStarted) {
            runnerStarted = true;
            setRunOutput('Loading the browser Python runtime…');
            iframe.src = '/static/practice-sandbox.html';
            runnerLoadTimeout = setTimeout(() => {
                if (runnerReady) return;
                runnerStarted = false;
                queuedRun = false;
                runButton.disabled = false;
                iframe.src = 'about:blank';
                setRunOutput('Python runtime did not load. Check your connection and try again.', true);
            }, 45000);
        }
    };

    const runExercise = () => {
        if (!selectedExercise) return;
        if (!runnerReady) {
            queuedRun = true;
            runButton.disabled = true;
            startRunner();
            return;
        }
        const runId = ++nextRunId;
        activeRunId = runId;
        runButton.disabled = true;
        setRunOutput('Running in the browser…');
        iframe.contentWindow.postMessage({
            type: 'run',
            runId,
            code: `${currentSource()}\n\n${selectedExercise.checks_code}`,
        }, '*');
        runTimeout = setTimeout(() => {
            if (activeRunId !== runId) return;
            activeRunId = null;
            runButton.disabled = false;
            setRunOutput('Execution timed out. The browser worker was stopped; try a smaller exercise.', true);
            runnerReady = false;
            runnerStarted = false;
            iframe.src = 'about:blank';
        }, 10000);
    };

    editor = new EditorView({
        state: EditorState.create({
            doc: '',
            extensions: [
                lineNumbers(),
                python(),
                oneDark,
                keymap.of([...defaultKeymap, indentWithTab]),
                EditorView.lineWrapping,
                EditorView.updateListener.of((update) => {
                    if (update.docChanged && !switching) queueSave();
                }),
            ],
        }),
        parent: editorHost,
    });

    exerciseList.forEach((exercise) => {
        const option = document.createElement('option');
        option.value = exercise.id;
        option.textContent = exercise.title;
        selector.append(option);
    });

    launcher.addEventListener('click', openPanel);
    document.getElementById('practice-close').addEventListener('click', () => {
        void closePanel();
    });
    document.getElementById('practice-collapse').addEventListener('click', (event) => {
        const collapsed = panel.classList.toggle('is-collapsed');
        event.currentTarget.setAttribute('aria-expanded', String(!collapsed));
        event.currentTarget.textContent = collapsed ? 'Expand' : 'Minimize';
        event.currentTarget.setAttribute(
            'aria-label', collapsed ? 'Expand workspace' : 'Collapse workspace',
        );
        resizeEditor();
    });
    document.getElementById('practice-maximize').addEventListener('click', (event) => {
        const maximized = panel.classList.toggle('is-maximized');
        event.currentTarget.setAttribute('aria-pressed', String(maximized));
        event.currentTarget.textContent = maximized ? 'Restore' : 'Maximize';
        resizeEditor();
    });
    selector.addEventListener('change', async () => {
        if (!(await saveWorkspace())) {
            selector.value = selectedExercise.id;
            return;
        }
        const exercise = exerciseList.find((item) => item.id === selector.value);
        if (exercise) await loadExercise(exercise);
    });
    resetButton.addEventListener('click', () => {
        if (!selectedExercise) return;
        if (currentSource() !== selectedExercise.starter_code && !window.confirm('Discard your edits and restore the starter code?')) return;
        setEditorSource(selectedExercise.starter_code);
        queueSave();
    });
    runButton.addEventListener('click', runExercise);
    document.getElementById('practice-open-from-lesson').addEventListener('click', openPanel);

    window.addEventListener('message', (event) => {
        if (
            event.source !== iframe.contentWindow
            || event.origin !== 'null'
            || !event.data
        ) return;
        if (event.data.type === 'ready') {
            clearTimeout(runnerLoadTimeout);
            runnerReady = true;
            runButton.disabled = switching;
            if (queuedRun) {
                queuedRun = false;
                runExercise();
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
            setRunOutput(event.data.text || 'Python runtime failed to load.', true);
            return;
        }
        if (event.data.type === 'run-started') {
            setRunOutput('Running checks…');
            return;
        }
        if (event.data.runId !== activeRunId) return;
        if (event.data.type === 'output') {
            output.textContent = `${output.textContent}${event.data.text}`.slice(0, 12000);
        } else if (event.data.type === 'done' || event.data.type === 'error' || event.data.type === 'timeout') {
            clearTimeout(runTimeout);
            activeRunId = null;
            runButton.disabled = false;
            setRunOutput(event.data.text, event.data.type !== 'done');
        }
    });
    void loadExercise(exerciseList[0]);
}
