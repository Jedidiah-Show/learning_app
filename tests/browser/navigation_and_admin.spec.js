const {test, expect} = require('@playwright/test');

// Navigation smoke test that deliberately uses direct URLs and visible text
// instead of sidebar CSS paths: nav items move between grouped menus.
async function registerLearner(page, prefix = 'navigation') {
  const suffix = Date.now();
  const username = `${prefix}-${suffix}`;
  await page.goto('/register');
  await page.getByLabel('Full Name').fill('Navigation Learner');
  await page.getByLabel('Username *').fill(username);
  await page.getByLabel('Email *').fill(`${username}@example.test`);
  await page.getByLabel('Password *', {exact: true}).fill('navigation-pass-123');
  await page.getByLabel('Confirm password *').fill('navigation-pass-123');
  await page.getByRole('button', {name: 'Create Account'}).click();
  await expect(page).toHaveURL(/\/onboarding$/);
  await page.getByRole('button', {name: 'Skip for now'}).click();
  return username;
}

test('learner can sign in through the login form', async ({page}) => {
  const username = await registerLearner(page);

  await page.goto('/profile');
  await page.getByRole('button', {name: 'Sign out'}).click();
  await expect(page).toHaveURL(/\/login$/);

  await page.getByLabel('Username or Email').fill(username);
  await page.getByLabel('Password', {exact: true}).fill('navigation-pass-123');
  await page.getByRole('button', {name: 'Sign in'}).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByText(/lessons complete/i).first()).toBeVisible();
});

test('pathway switch form updates the active specialisation', async ({page}) => {
  await registerLearner(page, 'pathway-switch');

  await page.goto('/');
  const switcher = page.getByRole('group', {name: 'Switch active pathway'});
  await expect(switcher).toBeVisible();
  const ml = switcher.getByRole('button', {name: 'ML', exact: true});
  await ml.click();
  await expect(ml).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByText(/Switched to Machine Learning/)).toBeVisible();

  await page.goto('/profile');
  await expect(page.getByRole('button', {name: 'Switch to AI Engineering'})).toBeVisible();
});

test('command palette opens with Ctrl+K and filters lessons', async ({page}) => {
  await registerLearner(page, 'palette-nav');

  await page.goto('/');
  await page.keyboard.press('Control+k');
  const palette = page.getByRole('dialog', {name: 'Quick navigation'});
  await expect(palette).toBeVisible();
  const input = palette.getByRole('combobox');
  await expect(input).toBeFocused();

  await input.fill('python');
  const results = palette.getByRole('option');
  await expect(results.first()).toBeVisible();
  await expect(results.filter({hasText: /python/i}).first()).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(palette).toBeHidden();
});

test('credential page is reachable for a learner', async ({page}) => {
  await registerLearner(page, 'credential-nav');
  await page.goto('/credential');
  await expect(page.getByRole('heading', {name: 'Course credential'})).toBeVisible();
});

test('administrator can sign in to the admin portal', async ({page}) => {
  // The browser smoke server is seeded with the standard learner account only.
  // Supply admin credentials when testing against a seeded environment.
  const email = process.env.BROWSER_ADMIN_EMAIL || 'admin@example.test';
  const password = process.env.BROWSER_ADMIN_PASSWORD || 'admin-pass-123';
  test.skip(
    !process.env.BROWSER_ADMIN_EMAIL && !process.env.BROWSER_ADMIN_PASSWORD,
    'Set BROWSER_ADMIN_EMAIL and BROWSER_ADMIN_PASSWORD to exercise admin sign-in.',
  );

  await page.goto('/admin/login');
  await page.getByLabel('Username or email').fill(email);
  await page.getByLabel('Password', {exact: true}).fill(password);
  await page.getByRole('button', {name: /Open admin portal/}).click();
  await expect(page).toHaveURL(/\/admin\/?$/);
  await expect(page.getByRole('heading', {name: 'Admin dashboard'})).toBeVisible();
});
