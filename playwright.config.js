const {defineConfig} = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/browser',
  timeout: 120_000,
  expect: {timeout: 10_000},
  use: {baseURL: 'http://127.0.0.1:4173', headless: true},
  reporter: 'list',
  webServer: {
    command: 'python3 tests/browser/serve_ide_smoke.py',
    url: 'http://127.0.0.1:4173/tests/browser/ide-smoke.html',
    reuseExistingServer: !process.env.CI,
    timeout: 15_000,
  },
});
