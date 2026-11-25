const {test, expect} = require('@playwright/test');

async function register(page) {
  const suffix = Date.now();
  await page.goto('/register');
  await page.getByLabel('Full Name').fill('Frontend Learner');
  await page.getByLabel('Username *').fill(`fe-${suffix}`);
  await page.getByLabel('Email *').fill(`fe-${suffix}@example.test`);
  await page.getByLabel('Password *', {exact: true}).fill('browser-test-pass-123');
  await page.getByLabel('Confirm password *').fill('browser-test-pass-123');
  await page.getByRole('button', {name: 'Create Account'}).click();
  await expect(page).toHaveURL(/\/onboarding$/);
  await page.getByRole('button', {name: 'Skip for now'}).click();
}

test('command palette exposes listbox option semantics to keyboard users', async ({page}) => {
  await register(page);
  await page.keyboard.press('Control+k');
  const dialog = page.locator('#command-palette');
  await expect(dialog).toBeVisible();
  const input = page.locator('#palette-input');
  await expect(input).toHaveAttribute('role', 'combobox');
  await expect(input).toHaveAttribute('aria-expanded', 'true');

  const options = page.locator('#palette-results [role="option"]');
  await expect(options.first()).toHaveAttribute('aria-selected', 'true');
  const firstId = await options.first().getAttribute('id');
  await expect(input).toHaveAttribute('aria-activedescendant', firstId);

  await input.focus();
  await page.keyboard.press('ArrowDown');
  const secondId = await options.nth(1).getAttribute('id');
  await expect(input).toHaveAttribute('aria-activedescendant', secondId);
  await expect(options.nth(1)).toHaveAttribute('aria-selected', 'true');
  await expect(options.first()).toHaveAttribute('aria-selected', 'false');

  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
  await expect(input).not.toHaveAttribute('aria-activedescendant', /.+/);
});

test('pathway switch stays visible on phones and practice CTA opens the panel', async ({page}) => {
  await register(page);
  await page.setViewportSize({width: 375, height: 812});
  await page.goto('/lesson/0.01');
  await expect(page.locator('.pathway-switch')).toBeVisible();

  const cta = page.locator('[data-open-practice]').first();
  await expect(cta).toBeVisible();
  await cta.click();
  await expect(page.locator('#practice-panel')).toBeVisible();
});
