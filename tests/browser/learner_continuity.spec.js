const {test, expect} = require('@playwright/test');

test('registration, saved lesson tasks, and tutor history survive a reload', async ({page}) => {
  const suffix = Date.now();
  await page.goto('/register');
  await page.getByLabel('Full Name').fill('Browser Learner');
  await page.getByLabel('Username *').fill(`browser-${suffix}`);
  await page.getByLabel('Email *').fill(`browser-${suffix}@example.test`);
  await page.getByLabel('Password *').fill('browser-test-pass-123');
  await page.getByLabel('Confirm password *').fill('browser-test-pass-123');
  await page.getByRole('button', {name: 'Create Account'}).click();

  await expect(page).toHaveURL(/\/onboarding$/);
  await page.getByRole('button', {name: 'Skip for now'}).click();
  await expect(page).toHaveURL(/\/onboarding\/pathway$/);
  await page.getByRole('button', {name: 'Skip for now'}).click();

  await page.goto('/lesson/0.01');
  const firstTask = page.locator('[data-lesson-tasks] input[type="checkbox"]').first();
  await expect(firstTask).toBeEnabled();
  await firstTask.check();
  await expect(page.locator('[data-task-progress-status]')).toHaveText(
    'Task progress saved to your account.',
  );
  await page.reload();
  await expect(page.locator('[data-task-progress-status]')).toHaveText(
    'Saved task progress loaded.',
  );
  await expect(firstTask).toBeChecked();

  await page.locator('#question').fill('Hello!');
  await page.locator('#ask-send').click();
  await expect(page.locator('.tutor-message-user').getByText('Hello!')).toBeVisible();
  await expect(page.locator('.tutor-message-assistant').filter({hasText: 'Ruach-AI'}).last()).toBeVisible();
  await page.reload();
  await expect(page.locator('.tutor-message-user').getByText('Hello!')).toBeVisible();

  await page.locator('#ask-reset').click();
  await expect(page.locator('#tutor-history-status')).toHaveText('Saved conversation cleared.');
  await page.reload();
  await expect(page.locator('.tutor-message-user').getByText('Hello!')).toHaveCount(0);
  await expect(page.locator('[data-task-progress-status]')).toHaveText(
    'Saved task progress loaded.',
  );
  await expect(firstTask).toBeChecked();
});
