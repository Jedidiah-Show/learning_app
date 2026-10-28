const {test, expect} = require('@playwright/test');

test('isolated Python IDE loads Pyodide and executes learner checks', async ({page}) => {
  const runtimeErrors = [];
  page.on('pageerror', (error) => runtimeErrors.push(error.message));
  page.on('console', (message) => { if (message.type() === 'error') runtimeErrors.push(message.text()); });
  page.on('requestfailed', (request) => runtimeErrors.push(`${request.url()}: ${request.failure()?.errorText}`));
  await page.goto('/tests/browser/ide-smoke.html');
  await expect(page.locator('#status')).toHaveText('Run completed', {timeout: 110_000});
  await expect(page.locator('#output')).toContainText('All checks passed.');
  expect(runtimeErrors).toEqual([]);
});
