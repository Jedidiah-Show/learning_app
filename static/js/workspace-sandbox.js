(() => {
    const pyodideVersion = '0.27.7';
    const runtimeIndexes = [
        new URL(`/static/pyodide/${pyodideVersion}/`, document.location.href).href,
        `https://cdn.jsdelivr.net/pyodide/v${pyodideVersion}/full/`,
        `https://unpkg.com/pyodide@${pyodideVersion}/`,
    ];
    const packageMap = {
        numpy: 'numpy', pandas: 'pandas', scipy: 'scipy', sympy: 'sympy',
        sklearn: 'scikit-learn', matplotlib: 'matplotlib', networkx: 'networkx',
    };
    const pytestShim = String.raw`
import sys
import types
import collections

class _Approx:
    def __init__(self, expected, rel=1e-6, abs=1e-12):
        self.expected = expected
        self.rel = rel
        self.abs = abs
    def __repr__(self):
        return f'approx({self.expected!r})'
    def __eq__(self, other):
        try:
            delta = abs(other - self.expected)
        except TypeError:
            return False
        return delta <= max(self.abs, self.rel * abs(self.expected))

class _Raises:
    def __init__(self, expected):
        self.expected = expected
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return exc_type is not None and issubclass(exc_type, self.expected)

_pytest = types.ModuleType('pytest')

def _approx(expected, rel=1e-6, abs=1e-12):
    return _Approx(expected, rel, abs)

_pytest.approx = _approx
_pytest.raises = _Raises
_pytest._pass = 'pass'
_pytest.skip = lambda reason='': (_ for _ in ()).throw(StopIteration(reason))

class _Mark:
    def __getattr__(self, name):
        def decorator(*args, **kwargs):
            if args and callable(args[0]):
                return args[0]
            return lambda f: f
        return decorator

_pytest.mark = _Mark()
_pytest.fixture = lambda *a, **k: (lambda f: f) if len(a) != 1 or not callable(a[0]) else a[0]
sys.modules['pytest'] = _pytest
`;
    const checksDriver = String.raw`
import importlib.util
import inspect
import json
import sys
import traceback
import types
from pathlib import Path

ROOT = Path('/project')
sys.path.insert(0, str(ROOT))

def load_module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

tests = sorted((ROOT / 'tests').glob('test_*.py')) if (ROOT / 'tests').is_dir() else []
passed, failed = [], []
if not tests:
    print('No tests/ directory found — nothing to run.')
else:
    for path in tests:
        module = load_module(path)
        for name in dir(module):
            if not name.startswith('test_'):
                continue
            fn = getattr(module, name)
            if not callable(fn):
                continue
            label = f'{path.name}::{name}'
            try:
                fn()
            except Exception:
                failed.append((label, traceback.format_exc()))
                print(f'FAILED {label}')
            else:
                passed.append(label)
                print(f'PASSED {label}')

print('')
print(f'{len(passed)} passed, {len(failed)} failed')
for label, tb in failed:
    print('')
    print('=' * 60)
    print(f'FAILED {label}')
    print(tb.rstrip())
`;
    const workerSource = `
        const runtimeIndexes = ${JSON.stringify(runtimeIndexes)};
        const packageMap = ${JSON.stringify(packageMap)};
        const pytestShim = ${JSON.stringify(pytestShim)};
        const checksDriver = ${JSON.stringify(checksDriver)};
        let pyodide;
        let output = '';
        const outputLimit = 12000;
        let currentRunId = null;
        const sendOutput = (text) => {
            if (output.length >= outputLimit) return;
            const remaining = outputLimit - output.length;
            const chunk = String(text).slice(0, remaining);
            output += chunk;
            self.postMessage({type: 'output', runId: currentRunId, text: chunk});
        };
        const loadRuntime = async () => {
            const failures = [];
            for (const indexURL of runtimeIndexes) {
                try {
                    importScripts(new URL('pyodide.js', indexURL).href);
                    return await loadPyodide({indexURL});
                } catch (error) {
                    failures.push(String(indexURL) + ': ' + (error && error.message ? error.message : String(error)));
                }
            }
            throw new Error('Python could not load from the app or either runtime CDN. ' + failures.join(' | '));
        };
        const mkdirRecursive = (fs, directory) => {
            const segments = directory.split('/').filter(Boolean);
            let current = '';
            for (const segment of segments) {
                current += '/' + segment;
                try { fs.mkdir(current); } catch (error) { /* exists */ }
            }
        };
        const seedFiles = (fs, files) => {
            for (const [relative, content] of Object.entries(files)) {
                const directory = relative.split('/').slice(0, -1).join('/');
                if (directory) mkdirRecursive(fs, '/project/' + directory);
                fs.writeFile('/project/' + relative, String(content));
            }
        };
        const neededPackages = (files) => {
            const needed = new Set();
            for (const content of Object.values(files)) {
                for (const line of String(content).split('\\n')) {
                    const match = line.match(/^\\s*(?:import|from)\\s+([A-Za-z_][A-Za-z0-9_.]*)/);
                    if (match) needed.add(match[1].split('.')[0]);
                }
            }
            return [...new Set([...needed].map((name) => packageMap[name]).filter(Boolean))];
        };
        loadRuntime().then((runtime) => {
            pyodide = runtime;
            pyodide.setStdout({batched: sendOutput});
            pyodide.setStderr({batched: sendOutput});
            self.fetch = () => Promise.reject(new Error('Network access is disabled in the workspace.'));
            self.XMLHttpRequest = class {
                open() {
                    throw new Error('Network access is disabled in the workspace.');
                }
            };
            self.WebSocket = undefined;
            self.EventSource = undefined;
            if (self.navigator) {
                self.navigator.sendBeacon = () => false;
            }
            self.importScripts = () => {
                throw new Error('Additional scripts are disabled in the workspace.');
            };
            self.WebTransport = undefined;
            self.Worker = undefined;
            self.SharedWorker = undefined;
            self.postMessage({type: 'ready'});
            self.onmessage = async ({data}) => {
                if (data.type !== 'run' && data.type !== 'checks') return;
                currentRunId = data.runId;
                output = '';
                self.postMessage({type: 'run-started', runId: currentRunId});
                try {
                    const files = data.files || {};
                    mkdirRecursive(pyodide.FS, '/project');
                    try { pyodide.FS.mkdir('/project'); } catch (error) { /* exists */ }
                    seedFiles(pyodide.FS, files);
                    pyodide.runPython('import os\\nos.chdir("/project")\\nimport sys\\nsys.path.insert(0, "/project")');
                    for (const pkg of neededPackages(files)) {
                        try {
                            await pyodide.loadPackage(pkg);
                        } catch (error) {
                            sendOutput('[workspace] could not load package ' + pkg + ': ' + (error && error.message ? error.message : String(error)) + '\\n');
                        }
                    }
                    if (data.type === 'checks') {
                        pyodide.runPython(pytestShim);
                        await pyodide.runPythonAsync(checksDriver);
                        self.postMessage({type: 'done', runId: currentRunId, text: output || 'Checks complete.'});
                        return;
                    }
                    const entry = data.entry || 'main.py';
                    const source = files[entry];
                    if (source === undefined) {
                        throw new Error('Entry file not found: ' + entry);
                    }
                    pyodide.globals.set('__name__', '__main__');
                    await pyodide.runPythonAsync(source, {filename: entry});
                    self.postMessage({type: 'done', runId: currentRunId, text: output || 'Done (no output).'});
                } catch (error) {
                    sendOutput(error && error.message ? error.message : String(error));
                    self.postMessage({type: 'error', runId: currentRunId, text: output || String(error)});
                }
            };
        }).catch((error) => self.postMessage({type: 'error', text: String(error)}));
    `;
    let workerUrl;
    let worker;
    let runTimer;
    let activeRunId = null;
    const appOrigin = (() => {
        try {
            return document.referrer ? new URL(document.referrer).origin : null;
        } catch (error) {
            return null;
        }
    })();
    const sendToParent = (message) => parent.postMessage(message, appOrigin || '*');
    const startWorker = () => {
        try {
            workerUrl ||= URL.createObjectURL(new Blob([workerSource], {type: 'text/javascript'}));
            worker = new Worker(workerUrl);
        } catch (error) {
            sendToParent({
                type: 'error',
                runId: null,
                text: `This browser blocked the isolated Python worker. Try another browser or allow blob workers. ${error?.message || error}`,
            });
            return;
        }
        worker.onmessage = ({data}) => {
            if (data.type === 'ready') sendToParent({type: 'ready'});
            else {
                if (data.type === 'done' || data.type === 'error') clearTimeout(runTimer);
                sendToParent(data);
            }
        };
        worker.onerror = (event) => sendToParent({
            type: 'error',
            runId: activeRunId,
            text: `The Python worker stopped${event.filename ? ` in ${event.filename}` : ''}${event.lineno ? ` at line ${event.lineno}` : ''}: ${event.message || 'unknown worker error'}`,
        });
        worker.onmessageerror = () => sendToParent({
            type: 'error',
            runId: activeRunId,
            text: 'The browser could not read a message from the Python worker. Reload the workspace and try again.',
        });
    };
    startWorker();
    addEventListener('message', (event) => {
        if (
            event.source !== parent
            || (appOrigin && event.origin !== appOrigin)
            || !event.data
            || (event.data.type !== 'run' && event.data.type !== 'checks')
        ) return;
        activeRunId = event.data.runId;
        clearTimeout(runTimer);
        sendToParent({type: 'run-started', runId: activeRunId});
        worker.postMessage(event.data);
        runTimer = setTimeout(() => {
            worker.terminate();
            sendToParent({type: 'timeout', runId: activeRunId, text: 'Execution exceeded the 20-second limit.'});
            startWorker();
        }, 20000);
    });
})();
