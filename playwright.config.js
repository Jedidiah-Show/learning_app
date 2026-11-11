const {defineConfig} = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const venvPython = path.join(
  __dirname,
  '.venv',
  process.platform === 'win32' ? 'Scripts' : 'bin',
  process.platform === 'win32' ? 'python.exe' : 'python',
);
const python = process.env.PYTHON || (
  fs.existsSync(venvPython) ? venvPython : 'python3'
);

module.exports = defineConfig({
  testDir: './tests/browser',
  timeout: 120_000,
  workers: 1,
  expect: {timeout: 10_000},
  use: {baseURL: 'http://127.0.0.1:4173', headless: true},
  reporter: 'list',
  webServer: {
    command: `"${python}" tests/browser/serve_ide_smoke.py`,
    url: 'http://127.0.0.1:4173/tests/browser/ide-smoke.html',
    reuseExistingServer: !process.env.CI,
    timeout: 15_000,
  },
});
