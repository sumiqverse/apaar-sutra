/**
 * APAAR-Sutra Node.js Integration Client Example
 * Demonstrates HMAC-SHA256 authenticated batch ingestion and status polling.
 */

const crypto = require('crypto');
const http = require('http');
const https = require('https');

class ApaarSutraNodeClient {
  constructor(baseUrl, clientId, clientSecret) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.clientId = clientId;
    this.clientSecret = clientSecret;
  }

  _signRequest(method, path, bodyString = '') {
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const nonce = 'n_' + crypto.randomBytes(8).toString('hex');
    const bodyHash = crypto.createHash('sha256').update(bodyString, 'utf8').digest('hex');

    // Canonical string: METHOD\nPATH\nTIMESTAMP\nNONCE\nBODY_HASH
    const canonicalString = `${method.toUpperCase()}\n${path}\n${timestamp}\n${nonce}\n${bodyHash}`;
    const signature = crypto
      .createHmac('sha256', this.clientSecret)
      .update(canonicalString, 'utf8')
      .digest('hex');

    return {
      'X-Client-ID': this.clientId,
      'X-Timestamp': timestamp,
      'X-Nonce': nonce,
      'X-Signature': signature,
    };
  }

  async _request(method, path, payload = null, customHeaders = {}) {
    const url = new URL(this.baseUrl + path);
    const bodyString = payload ? JSON.stringify(payload) : '';

    const authHeaders = this._signRequest(method, path, bodyString);
    const headers = {
      'Accept': 'application/json',
      ...authHeaders,
      ...customHeaders,
    };

    if (bodyString) {
      headers['Content-Type'] = 'application/json';
      headers['Content-Length'] = Buffer.byteLength(bodyString);
    }

    const transport = url.protocol === 'https:' ? https : http;

    return new Promise((resolve, reject) => {
      const req = transport.request(
        {
          hostname: url.hostname,
          port: url.port || (url.protocol === 'https:' ? 443 : 80),
          path: url.pathname + url.search,
          method: method.toUpperCase(),
          headers: headers,
        },
        (res) => {
          let data = '';
          res.on('data', (chunk) => {
            data += chunk;
          });
          res.on('end', () => {
            if (res.statusCode >= 200 && res.statusCode < 300) {
              try {
                resolve(data ? JSON.parse(data) : {});
              } catch (err) {
                resolve({ raw: data });
              }
            } else {
              reject(new Error(`HTTP ${res.statusCode}: ${data}`));
            }
          });
        }
      );

      req.on('error', (err) => reject(err));
      if (bodyString) {
        req.write(bodyString);
      }
      req.end();
    });
  }

  async pushStudentsBatch(students, idempotencyKey = null) {
    const idKey = idempotencyKey || 'idemp_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
    return this._request('POST', '/api/v1/integration/students', students, {
      'Idempotency-Key': idKey,
    });
  }

  async getBatchStatus(batchId) {
    return this._request('GET', `/api/v1/integration/batches/${batchId}`);
  }
}

// --- Example Execution ---
async function runDemo() {
  const client = new ApaarSutraNodeClient(
    'http://localhost:8000',
    'erp_demo_client_001',
    'sec_demo_secret_key_sutrapass_2026'
  );

  const sampleStudents = [
    {
      student_ref_id: 'NODE-ERP-' + Date.now(),
      apaar_id: '123456789012',
      name: 'Rohan Deshmukh',
      dob: '2004-03-22',
      gender: 'MALE',
      parent_name: 'Suresh Deshmukh',
      contact: { email: 'rohan.d@example.edu.in', phone: '9822012345' },
      program_name: 'B.Tech Mechanical Engineering',
      branch: 'MECH',
      academic_year: '2025-26',
      admission_category: 'GEN',
      quota_type: 'REGULAR',
      is_nri: false,
      admission_date: '2025-07-18',
      status: 'ACTIVE',
    },
  ];

  console.log('[Node Client] Pushing students batch...');
  try {
    const result = await client.pushStudentsBatch(sampleStudents);
    console.log('[Node Client] Result:', result);
    if (result.batch_id) {
      console.log('[Node Client] Polling batch status...');
      const status = await client.getBatchStatus(result.batch_id);
      console.log('[Node Client] Batch status:', status);
    }
  } catch (err) {
    console.log('[Node Client] Note: Connect to local server on port 8000 to execute:', err.message);
  }
}

if (require.main === module) {
  runDemo();
}

module.exports = { ApaarSutraNodeClient };
