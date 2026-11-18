import { defineConfig, devices } from '@playwright/test';

// No webServer block: every test starts its own app process on a free port with its own
// fresh DATA_DIR (tests/support/fixtures.ts). That is what makes seat-count assertions
// safe under parallel workers, and lets a test stop and restart "the" server for AC-07.
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: true,
  retries: 0, // a retry would hide exactly the flake this event is about
  timeout: 30_000,
  reporter: [['list'], ['json', { outputFile: 'test-results/results.json' }]],
  use: {
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'api', testDir: './tests/api' },
    { name: 'ui', testDir: './tests/ui', use: { ...devices['Desktop Chrome'] } },
  ],
});
