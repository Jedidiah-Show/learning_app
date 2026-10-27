(() => {
    const pyodideVersion = '0.27.7';
    const pyodideUrl = `https://cdn.jsdelivr.net/pyodide/v${pyodideVersion}/full/pyodide.js`;
    const workerSource = `
        importScripts(${JSON.stringify(pyodideUrl)});
        const indexURL = ${JSON.stringify(`https://cdn.jsdelivr.net/pyodide/v${pyodideVersion}/full/`)};
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
        loadPyodide({indexURL}).then((runtime) => {
            pyodide = runtime;
            pyodide.setStdout({batched: sendOutput});
            pyodide.setStderr({batched: sendOutput});
            self.fetch = () => Promise.reject(new Error('Network access is disabled in practice exercises.'));
            self.XMLHttpRequest = class {
                open() {
                    throw new Error('Network access is disabled in practice exercises.');
                }
            };
            self.WebSocket = undefined;
            self.EventSource = undefined;
            if (self.navigator) {
                self.navigator.sendBeacon = () => false;
            }
            self.importScripts = () => {
                throw new Error('Additional scripts are disabled in practice exercises.');
            };
            self.WebTransport = undefined;
            self.Worker = undefined;
            self.SharedWorker = undefined;
            self.postMessage({type: 'ready'});
            self.onmessage = async ({data}) => {
                if (data.type !== 'run') return;
                currentRunId = data.runId;
                output = '';
                self.postMessage({type: 'run-started', runId: currentRunId});
                try {
                    await pyodide.runPythonAsync(data.code);
                    self.postMessage({type: 'done', runId: currentRunId, text: output || 'Checks passed (no output).'});
                } catch (error) {
                    sendOutput(error);
                    self.postMessage({type: 'error', runId: currentRunId, text: output || String(error)});
                }
            };
        }).catch((error) => self.postMessage({type: 'error', text: String(error)}));
    `;
    const workerUrl = URL.createObjectURL(new Blob([workerSource], {type: 'text/javascript'}));
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
        worker = new Worker(workerUrl);
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
            text: event.message || 'Python runtime failed to load.',
        });
    };
    startWorker();
    addEventListener('message', (event) => {
        if (
            event.source !== parent
            || (appOrigin && event.origin !== appOrigin)
            || !event.data
            || event.data.type !== 'run'
        ) return;
        activeRunId = event.data.runId;
        clearTimeout(runTimer);
        sendToParent({type: 'run-started', runId: event.data.runId});
        worker.postMessage(event.data);
        runTimer = setTimeout(() => {
            worker.terminate();
            sendToParent({type: 'timeout', runId: event.data.runId, text: 'Execution exceeded the 8-second limit.'});
            startWorker();
        }, 8000);
    });
})();
