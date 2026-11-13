import http from 'k6/http';
import { check, sleep } from 'k6';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.2/index.js';

const HOST = __ENV.HOST || 'http://127.0.0.1:18080';

const PUBLIC_PATHS = ['/healthz', '/readyz', '/.well-known/jwks.json', '/login'];
const AUTHED_PATHS = [
  '/',
  '/lessons',
  '/arena/',
  '/arena/problems',
  '/progress',
  '/projects',
  '/portfolio',
  '/quizzes',
  '/community',
  '/search?q=python',
  '/passport',
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
    ramp_to_5000: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 100 },
        { duration: '60s', target: 500 },
        { duration: '90s', target: 1000 },
        { duration: '120s', target: 2500 },
        { duration: '120s', target: 5000 },
        { duration: '300s', target: 5000 },
      ],
      gracefulRampDown: '10s',
    },
  },
};

export default function () {
  const jar = http.cookieJar();
  const loginPage = http.get(`${HOST}/login`, { tags: { name: 'login' } });
  const token = csrfToken(loginPage.body);
  http.post(
    `${HOST}/login`,
    { username: 'loadtest@example.com', password: 'loadtest-password', csrf_token: token },
    { jar, redirects: 5, tags: { name: 'login-post' } },
  );
  for (const path of AUTHED_PATHS) {
    const res = http.get(`${HOST}${path}`, {
      jar,
      redirects: 5,
      tags: { name: path },
    });
    check(res, { [`authed ${path} == 200`]: (r) => r.status === 200 });
  }
  sleep(1 + Math.random() * 2);
}

export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: ' ', enableColors: false }),
    '/tmp/opencode/task44_ramp_summary.json': JSON.stringify(data, null, 2),
  };
}
