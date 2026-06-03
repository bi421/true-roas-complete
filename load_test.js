import http from 'k6/http';
import { check, sleep } from 'k6';
import { crypto } from 'k6/crypto';

/**
 * TrueROAS v2.1 Load Test Suite
 * Requirements:
 * - Sync: 1000 RPS across 50 tenants
 * - Metrics: 500 RPS for 5 mins
 * - Webhooks: 10,000 events in 1 min (~167 RPS)
 */

const API_URL = __ENV.API_URL || 'http://localhost:8001';
// We use pre-generated tokens for 50 tenants to avoid overhead of JWT signing in the loop
const TENANT_TOKENS = JSON.parse(open('./tenant_tokens.json')); 
const SHOPIFY_SECRET = __ENV.SHOPIFY_API_SECRET || 'test_secret';

export const options = {
    scenarios: {
        // a) /api/v1/sync: 1000 RPS
        sync_load: {
            executor: 'constant-arrival-rate',
            rate: 1000,
            timeUnit: '1s',
            duration: '2m',
            preAllocatedVUs: 100,
            maxVUs: 500,
        },
        // b) /api/v1/metrics: 500 RPS for 5 mins
        metrics_load: {
            executor: 'constant-arrival-rate',
            rate: 500,
            timeUnit: '1s',
            duration: '5m',
            preAllocatedVUs: 50,
            maxVUs: 200,
        },
        // c) Shopify webhook: 10,000 refunds in 1 min
        webhook_spike: {
            executor: 'per-vu-iterations',
            vus: 50,
            iterations: 200, // 50 * 200 = 10,000 total
            maxDuration: '1m',
            startTime: '1m', // Start after load initializes
        },
        // Spike Test: 10x traffic increase simulation
        traffic_spike: {
            executor: 'ramping-arrival-rate',
            startRate: 100,
            timeUnit: '1s',
            preAllocatedVUs: 50,
            maxVUs: 1000,
            stages: [
                { duration: '30s', target: 100 },
                { duration: '1s', target: 1000 }, // 10x spike in 1 second
                { duration: '1m', target: 1000 },
                { duration: '30s', target: 100 },
            ],
            startTime: '6m',
        },
    },
    thresholds: {
        'http_req_duration': ['p(95)<500', 'p(99)<2000'], // p95 < 500ms, p99 < 2000ms
        'http_req_failed': ['rate<0.001'],               // Error rate < 0.1%
    },
};

export default function () {
    // This default function handles scenario logic based on scenario name
}

export function sync_load() {
    const tenant_id = `tenant_${Math.floor(Math.random() * 50)}`;
    const token = TENANT_TOKENS[tenant_id];
    const params = { headers: { 'Authorization': `Bearer ${token}` } };
    const res = http.post(`${API_URL}/api/v1/sync`, JSON.stringify({}), params);
    
    check(res, { 'sync status is 202': (r) => r.status === 202 });
}

export function metrics_load() {
    const tenant_id = `tenant_${Math.floor(Math.random() * 50)}`;
    const token = TENANT_TOKENS[tenant_id];
    const params = { headers: { 'Authorization': `Bearer ${token}` } };
    const res = http.get(`${API_URL}/api/v1/metrics`, params);
    
    check(res, { 'metrics status is 200': (r) => r.status === 200 });
}

export function webhook_spike() {
    const body = JSON.stringify({
        id: Math.floor(Math.random() * 1000000),
        order_id: 12345,
        transactions: [{ amount: "50.00" }],
        currency: "USD"
    });
    
    // Generate HMAC signature
    const hasher = crypto.createHMAC('sha256', SHOPIFY_SECRET);
    hasher.update(body);
    const hmac = hasher.digest('base64');

    const params = {
        headers: {
            'X-Shopify-Topic': 'refunds/create',
            'X-Shopify-Shop-Domain': 'test-store.myshopify.com',
            'X-Shopify-Hmac-Sha256': hmac,
            'Content-Type': 'application/json',
        },
    };

    const res = http.post(`${API_URL}/api/v1/webhooks/shopify`, body, params);
    check(res, { 'webhook accepted': (r) => r.status === 200 || r.status === 202 });
}

export function traffic_spike() {
    metrics_load(); // Use metrics endpoint to test spike resilience
}