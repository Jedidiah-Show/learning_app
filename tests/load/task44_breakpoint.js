import http from 'k6/http';
import { check, sleep } from 'k6';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.2/index.js';

const HOST = __ENV.HOST || 'http://127.0.0.1:18080';

const PUBLIC_PATHS = ['/healthz', '/login'];
const AUTHED_PATHS = [
  '/',
  '/lessons',
  '/arena/',
  '/arena/problems',
  '/progress',
  '/projects',
  '/portfolio',
];

const TOTAL = 10 + AUTHED_PATHS.length;

function csrfToken(html) {
  const match = html.match(/name="csrf_token" value="([^"]+)"/);
  return match ? match[1] : null;
}

export const options = {
  scenarios: {
    breakpoint: {
      executor: 'ramping-arrival-rate',
      startRate: 5,
      timeUnit: '1s',
      preAllocatedVUs: 200,
      maxVUs: 3000,
      stages: [
        { duration: '30s', target: 5 },
        { duration: '30s', target: 20 },
        { duration: '30s', target: 40 },
        { duration: '30s', target: 80 },
        { duration: '30s', target: 160 },
        { duration: '30s', target: 320 },
      ],
      gracefulStop: '30s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<2000'],
    checks: ['rate>0.99'],
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
}

export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: ' ', enableColors: false }),
    '/tmp/opencode/task44_breakpoint_summary.json': JSON.stringify(data, null, 2),
  };
}
