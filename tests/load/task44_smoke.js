import http from 'k6/http';
import { check, sleep } from 'k6';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.2/index.js';

const HOST = __ENV.HOST || 'http://127.0.0.1:18080';

const PUBLIC_PATHS = [
  '/healthz',
  '/readyz',
  '/.well-known/jwks.json',
  '/login',
  '/register',
];

const AUTHED_PATHS = [
  '/',
  '/lessons',
  '/arena/',
  '/arena/ai-engineering',
  '/arena/problems',
  '/progress',
  '/projects',
  '/portfolio',
  '/quizzes',
  '/community',
  '/search?q=python',
  '/passport',
  '/passport/download',
  '/achievements',
  '/gates',
  '/notifications',
  '/review',
  '/settings',
  '/specializations/machine-learning',
];

function csrfToken(html) {
  const match = html.match(/name="csrf_token" value="([^"]+)"/);
  return match ? match[1] : null;
}

export const options = {
  scenarios: {
    smoke: {
      executor: 'per-vu-iterations',
      vus: 1,
      iterations: 1,
      exec: 'smoke',
      maxDuration: '2m',
    },
  },
};

export function smoke() {
  const jar = http.cookieJar();
  for (const path of PUBLIC_PATHS) {
    const res = http.get(`${HOST}${path}`, {
      tags: { name: path, group: 'public' },
      redirects: 5,
    });
    check(res, { [`public ${path} == 200`]: (r) => r.status === 200 });
  }
  const loginPage = http.get(`${HOST}/login`);
  const token = csrfToken(loginPage.body);
  check(loginPage, { 'login page has csrf token': () => token !== null });
  const login = http.post(
    `${HOST}/login`,
    { username: 'loadtest@example.com', password: 'loadtest-password', csrf_token: token },
    { jar, redirects: 5 },
  );
  check(login, {
    'login redirected (3xx)': (r) => r.status === 302 || r.status === 200,
  });
  const authed = AUTHED_PATHS;
  for (const path of authed) {
    const res = http.get(`${HOST}${path}`, {
      jar,
      tags: { name: path, group: 'authed' },
      redirects: 5,
    });
    check(res, { [`authed ${path} == 200`]: (r) => r.status === 200 });
  }
}

export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: ' ', enableColors: false }),
  };
}
