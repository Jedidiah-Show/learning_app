const {test, expect} = require('@playwright/test');

async function register(page, prefix) {
  const suffix = Date.now();
  const username = `${prefix}-${suffix}`;
  await page.goto('/register');
  await page.getByLabel('Full Name').fill('Foundations Learner');
  await page.getByLabel('Username *').fill(username);
  await page.getByLabel('Email *').fill(`${username}@example.test`);
  await page.getByLabel('Password *', {exact: true}).fill('browser-test-pass-123');
  await page.getByLabel('Confirm password *').fill('browser-test-pass-123');
  await page.getByRole('button', {name: 'Create Account'}).click();
  await expect(page).toHaveURL(/\/onboarding$/);
  await page.getByRole('button', {name: 'Skip for now'}).click();
}

test('foundations quiz unlocks the next lesson and learner pages stay accessible', async ({page}) => {
  await register(page, 'foundations');

  await page.goto('/foundations');
  const start = page.locator('a[href="/specializations/shared-foundations/lessons/sf.00.01"]').first();
  await expect(start).toBeVisible();
  await start.click();
  await expect(page).toHaveURL(/\/specializations\/shared-foundations\/lessons\/sf\.00\.01$/);
  await expect(page.getByRole('heading', {name: 'Variables and Types'})).toBeVisible();
  await expect(page.getByText('Next lesson locked', {exact: false})).toBeVisible();

  // Correct answer for sf.00.01 is index 1 ("3").
  await page.locator('input[name="answer"][value="1"]').check();
  await page.getByRole('button', {name: 'Check answer'}).click();
  await expect(page.getByText('Completed · review mode')).toBeVisible();

  const next = page.getByRole('link', {name: /Next lesson: Control Flow/});
  await expect(next).toBeVisible();
  await next.click();
  await expect(page).toHaveURL(/\/sf\.00\.02$/);
  await expect(page.getByRole('heading', {name: 'Control Flow'})).toBeVisible();

  for (const [path, heading] of [
    ['/passport', 'Skill Passport'],
    ['/mastery', 'Concept mastery'],
    ['/portfolio', 'Verified engineering portfolio'],
  ]) {
    await page.goto(path);
    await expect(page.getByRole('heading', {name: heading, exact: false}).first()).toBeVisible();
  }
});
