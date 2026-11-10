// Deterministic, anonymous client for case.strategy-contract.v1.
// No registration, free-text upload, arbitrary plan execution, or bundled runtime.
import { createHash, randomBytes, randomUUID } from 'node:crypto';
import { performance } from 'node:perf_hooks';

export const STRATEGY_CONTRACT = Object.freeze({
  product: 'fbsir-industry-scene-researcher',
  baseUrl: 'https://api2.u3w.com/case-research',
  developmentBaseUrl: 'http://127.0.0.1:8767',
  resolvePath: '/v1/strategies/resolve',
  feedbackPath: '/v1/feedback',
  timeoutMs: 3000,
  maxRequestBytes: 16384,
  maxResponseBytes: 65536,
  expirySeconds: 600,
  receiveToleranceSeconds: 30
});

const REQUEST_KEYS = ['schema', 'request_id', 'consumer', 'intent_revision', 'brief_version', 'brief_digest', 'mode', 'demand', 'supply', 'budget', 'capabilities'];
const RESPONSE_KEYS = ['schema', 'request_id', 'intent_revision', 'brief_version', 'request_digest', 'decision_id', 'status', 'catalog_revision', 'strategy', 'plan', 'reason_codes', 'issued_at', 'expires_at'];
const PLAN_KEYS = ['query_axes', 'source_classes', 'checks', 'stop_rules', 'budget'];
const BUDGET_KEYS = ['max_queries', 'max_reads', 'max_cases', 'max_rounds'];
const CELL_KEYS = ['value', 'origin', 'status', 'evidence_version'];
const MODES = new Set(['new_research', 'update_research', 'verify_only', 'compare_only', 'pilot_review']);
const NETWORK_MODES = new Set(['new_research', 'update_research']);
const ORIGINS = new Set(['user_explicit', 'derived', 'unknown']);
const STATUSES = new Set(['known', 'unknown', 'conflict']);
const CAPABILITIES = new Set(['web_search', 'page_read', 'file_read']);
const REASON_CODES = new Set(['goal_match', 'unknown_preserved', 'conflict_preserved', 'native_short_path', 'no_active_strategy', 'capability_limited']);
const DECISION_STATUSES = new Set(['selected', 'skipped', 'no_match']);
const QUERY_AXES = new Set(['same_industry', 'same_mechanism', 'independent_outcomes', 'counterevidence', 'implementation_conditions']);
const SOURCE_CLASSES = new Set(['primary', 'independent', 'complementary', 'vendor_disclosed']);
const CHECKS = new Set(['subject_period', 'denominator_metric', 'cost_resources', 'independence', 'counterevidence', 'alternative_explanation', 'transfer_conditions', 'human_review', 'baseline_stop_rule']);
const STOP_RULES = new Set(['budget_exhausted', 'material_conflict_unresolved', 'source_unavailable', 'no_transfer_baseline']);
const DEMAND_ENUMS = {
  goal: new Set(['compare_cases', 'vendor_case', 'pilot_design', 'pilot_review', 'unknown']),
  context: new Set(['customer_service', 'process_operations', 'knowledge_work', 'other', 'unknown']),
  constraints: new Set(['specified', 'partial', 'unknown'])
};
const SUPPLY_ENUMS = {
  relation: new Set(['same_industry', 'same_mechanism', 'cross_industry', 'unknown']),
  evidence: new Set(['primary', 'complementary', 'vendor_only', 'mixed', 'unknown']),
  applicability: new Set(['known', 'partial', 'unknown'])
};
const BUDGET_LIMITS = { max_queries: [0, 12], max_reads: [0, 20], max_cases: [1, 6], max_rounds: [1, 2] };
const VERSION_PATTERN = /^[A-Za-z0-9.+_-]{1,48}$/;
const STRATEGY_ID_PATTERN = /^[a-z][a-z0-9-]{2,47}$/;
const HEX_64_PATTERN = /^[0-9a-f]{64}$/;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const REQUIRED_PLAN_CHECKS = ['subject_period', 'denominator_metric', 'independence', 'counterevidence', 'transfer_conditions'];
const FEEDBACK_KEYS = ['schema', 'feedback_id', 'decision_id', 'request_digest', 'consent', 'metrics'];
const METRIC_KEYS = ['queries', 'reads', 'cases_checked', 'cases_usable', 'critical_fields_total', 'critical_fields_supported', 'transfer_conditions_total', 'transfer_conditions_met', 'transfer_conditions_unknown', 'counterevidence_checked', 'elapsed_ms', 'user_relevance', 'adoption'];

export class StrategyClientError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'StrategyClientError';
    this.code = code;
  }
}

function fail(code, message) {
  throw new StrategyClientError(code, message);
}

function isObject(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function exactKeys(value, keys, code) {
  if (!isObject(value)) fail(code, 'Expected a plain object');
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) {
    fail(code, 'Object fields do not match the closed contract');
  }
}

function integer(value, min, max, code) {
  if (!Number.isSafeInteger(value) || value < min || value > max) fail(code, 'Integer is outside the allowed range');
}

function string(value, code, maxLength = 256) {
  if (typeof value !== 'string' || value.length < 1 || value.length > maxLength) fail(code, 'Invalid string');
  validateUnicode(value);
}

function uuid(value, code) {
  string(value, code, 36);
  if (!UUID_PATTERN.test(value)) fail(code, 'UUID must use canonical lowercase 8-4-4-4-12 form');
}

function validateUnicode(value) {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(index + 1);
      if (!(next >= 0xdc00 && next <= 0xdfff)) fail('invalid_unicode', 'Unpaired high surrogate');
      index += 1;
    } else if (code >= 0xdc00 && code <= 0xdfff) {
      fail('invalid_unicode', 'Unpaired low surrogate');
    }
  }
}

function normalizeJson(value, depth = 0, seen = new Set()) {
  if (depth > 64) fail('json_too_deep', 'JSON nesting exceeds 64');
  if (value === null || typeof value === 'boolean') return value;
  if (typeof value === 'string') {
    validateUnicode(value);
    return value;
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value) || !Number.isSafeInteger(value)) fail('integers_only', 'Only finite safe integers are allowed');
    return value;
  }
  if (typeof value !== 'object') fail('invalid_json_value', 'Unsupported JSON value');
  if (seen.has(value)) fail('cyclic_json', 'Cyclic JSON is not allowed');
  seen.add(value);
  let result;
  if (Array.isArray(value)) {
    result = value.map((item) => normalizeJson(item, depth + 1, seen));
  } else {
    if (!isObject(value)) fail('plain_objects_only', 'Only plain JSON objects are allowed');
    result = Object.create(null);
    for (const key of Object.keys(value).sort()) {
      validateUnicode(key);
      result[key] = normalizeJson(value[key], depth + 1, seen);
    }
  }
  seen.delete(value);
  return result;
}

export function canonicalJson(value) {
  return JSON.stringify(normalizeJson(value));
}

class StrictJsonParser {
  constructor(text, allowFiniteNumbers) {
    this.text = text;
    this.index = 0;
    this.nodes = 0;
    this.allowFiniteNumbers = allowFiniteNumbers;
  }

  parse() {
    this.whitespace();
    const value = this.value(0);
    this.whitespace();
    if (this.index !== this.text.length) fail('invalid_json', 'Trailing JSON content');
    return value;
  }

  whitespace() {
    while (this.index < this.text.length && /[\x20\x09\x0a\x0d]/.test(this.text[this.index])) this.index += 1;
  }

  value(depth) {
    if (depth > 64 || ++this.nodes > 100000) fail('json_limit', 'JSON depth or node limit exceeded');
    const char = this.text[this.index];
    if (char === '{') return this.object(depth);
    if (char === '[') return this.array(depth);
    if (char === '"') return this.string();
    if (char === '-' || (char >= '0' && char <= '9')) return this.number();
    for (const [literal, value] of [['true', true], ['false', false], ['null', null]]) {
      if (this.text.startsWith(literal, this.index)) {
        this.index += literal.length;
        return value;
      }
    }
    return fail('invalid_json', 'Unexpected JSON token');
  }

  object(depth) {
    this.index += 1;
    this.whitespace();
    const result = Object.create(null);
    const keys = new Set();
    if (this.text[this.index] === '}') {
      this.index += 1;
      return result;
    }
    while (this.index < this.text.length) {
      if (this.text[this.index] !== '"') fail('invalid_json', 'Object key must be a string');
      const key = this.string();
      if (keys.has(key)) fail('duplicate_key', 'Duplicate JSON object key');
      keys.add(key);
      this.whitespace();
      if (this.text[this.index] !== ':') fail('invalid_json', 'Missing object colon');
      this.index += 1;
      this.whitespace();
      result[key] = this.value(depth + 1);
      this.whitespace();
      if (this.text[this.index] === '}') {
        this.index += 1;
        return result;
      }
      if (this.text[this.index] !== ',') fail('invalid_json', 'Missing object comma');
      this.index += 1;
      this.whitespace();
    }
    return fail('invalid_json', 'Unterminated object');
  }

  array(depth) {
    this.index += 1;
    this.whitespace();
    const result = [];
    if (this.text[this.index] === ']') {
      this.index += 1;
      return result;
    }
    while (this.index < this.text.length) {
      result.push(this.value(depth + 1));
      this.whitespace();
      if (this.text[this.index] === ']') {
        this.index += 1;
        return result;
      }
      if (this.text[this.index] !== ',') fail('invalid_json', 'Missing array comma');
      this.index += 1;
      this.whitespace();
    }
    return fail('invalid_json', 'Unterminated array');
  }

  string() {
    const start = this.index;
    this.index += 1;
    while (this.index < this.text.length) {
      const char = this.text[this.index];
      if (char === '"') {
        this.index += 1;
        const raw = this.text.slice(start, this.index);
        let value;
        try {
          value = JSON.parse(raw);
        } catch {
          return fail('invalid_json', 'Invalid JSON string');
        }
        validateUnicode(value);
        return value;
      }
      if (char.charCodeAt(0) < 0x20) fail('invalid_json', 'Control character in string');
      if (char === '\\') {
        const escape = this.text[this.index + 1];
        if (!'"\\/bfnrtu'.includes(escape)) fail('invalid_json', 'Invalid string escape');
        this.index += escape === 'u' ? 6 : 2;
        if (this.index > this.text.length) fail('invalid_json', 'Incomplete string escape');
      } else {
        this.index += 1;
      }
    }
    return fail('invalid_json', 'Unterminated string');
  }

  number() {
    const pattern = this.allowFiniteNumbers ? /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/ : /^-?(?:0|[1-9][0-9]*)/;
    const match = pattern.exec(this.text.slice(this.index));
    if (!match) fail('integers_only', 'Invalid integer');
    this.index += match[0].length;
    const next = this.text[this.index];
    if (!this.allowFiniteNumbers && (next === '.' || next === 'e' || next === 'E')) fail('integers_only', 'Floating point and exponent numbers are not allowed');
    const value = Number(match[0]);
    if (this.allowFiniteNumbers ? !Number.isFinite(value) : !Number.isSafeInteger(value)) fail('invalid_number', 'Number exceeds the allowed finite or safe-integer range');
    return value;
  }
}

export function parseJsonStrict(text, maxBytes = STRATEGY_CONTRACT.maxResponseBytes, { allowFiniteNumbers = false } = {}) {
  if (typeof text !== 'string' || Buffer.byteLength(text, 'utf8') > maxBytes) fail('json_size_limit', 'JSON text exceeds the size limit');
  return new StrictJsonParser(text, allowFiniteNumbers).parse();
}

function sha256Bytes(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

export function createTaskSalt() {
  return randomBytes(32);
}

export function computeBriefDigest(effectiveLocalBrief, salt) {
  if (!Buffer.isBuffer(salt) && !(salt instanceof Uint8Array)) fail('invalid_salt', 'Salt must be raw bytes');
  if (salt.length !== 32) fail('invalid_salt', 'Salt must contain exactly 32 bytes');
  const canonical = Buffer.from(canonicalJson(effectiveLocalBrief), 'utf8');
  return createHash('sha256').update(Buffer.from(salt)).update(canonical).digest('hex');
}

function validateCell(cell, valueEnum) {
  exactKeys(cell, CELL_KEYS, 'invalid_cell_fields');
  if (!ORIGINS.has(cell.origin) || !STATUSES.has(cell.status)) fail('invalid_cell_enum', 'Invalid cell origin or status');
  if (cell.evidence_version !== null) integer(cell.evidence_version, 1, 1000000, 'invalid_evidence_version');
  if (cell.status === 'unknown' || cell.status === 'conflict') {
    if (cell.value !== 'unknown') fail('unknown_conflict_projection', 'Unknown or conflict must project value=unknown');
  }
  if (cell.status === 'unknown' && (cell.origin !== 'unknown' || cell.evidence_version !== null)) {
    fail('unknown_conflict_projection', 'Unknown requires unknown origin and null evidence version');
  }
  if (cell.status === 'known' && (cell.value === 'unknown' || cell.origin === 'unknown')) {
    fail('invalid_known_cell', 'Known cell requires a known value and non-unknown origin');
  }
  if (!valueEnum.has(cell.value)) fail('invalid_cell_value', 'Cell value is outside the closed enum');
}

function validateSide(side, fields, enums) {
  exactKeys(side, fields, 'invalid_side_fields');
  for (const field of fields) validateCell(side[field], enums[field]);
}

function validateBudget(budget) {
  exactKeys(budget, BUDGET_KEYS, 'invalid_budget_fields');
  for (const key of BUDGET_KEYS) integer(budget[key], BUDGET_LIMITS[key][0], BUDGET_LIMITS[key][1], 'invalid_budget');
}

export function buildIntentRequest(input) {
  const localKeys = ['requestId', 'consumerVersion', 'intentRevision', 'briefVersion', 'mode', 'demand', 'supply', 'budget', 'capabilities', 'effectiveLocalBrief', 'salt'];
  exactKeys(input, localKeys, 'invalid_local_request_fields');
  uuid(input.requestId, 'invalid_request_id');
  string(input.consumerVersion, 'invalid_consumer_version', 48);
  if (!VERSION_PATTERN.test(input.consumerVersion)) fail('invalid_consumer_version', 'Consumer version does not match the contract');
  integer(input.intentRevision, 1, 1000000, 'invalid_intent_revision');
  integer(input.briefVersion, 1, 1000000, 'invalid_brief_version');
  if (!MODES.has(input.mode)) fail('invalid_mode', 'Mode is outside the closed enum');
  validateSide(input.demand, ['goal', 'context', 'constraints'], DEMAND_ENUMS);
  validateSide(input.supply, ['relation', 'evidence', 'applicability'], SUPPLY_ENUMS);
  validateBudget(input.budget);
  if (!Array.isArray(input.capabilities) || input.capabilities.length > 3 || new Set(input.capabilities).size !== input.capabilities.length) fail('invalid_capabilities', 'Capabilities must be a unique array of at most three host observations');
  for (const capability of input.capabilities) {
    if (!CAPABILITIES.has(capability)) fail('invalid_capabilities', 'Capability is outside the closed enum');
  }
  const body = {
    schema: 'case.intent.v1',
    request_id: input.requestId,
    consumer: { product: STRATEGY_CONTRACT.product, version: input.consumerVersion },
    intent_revision: input.intentRevision,
    brief_version: input.briefVersion,
    brief_digest: computeBriefDigest(input.effectiveLocalBrief, input.salt),
    mode: input.mode,
    demand: input.demand,
    supply: input.supply,
    budget: input.budget,
    capabilities: input.capabilities
  };
  exactKeys(body, REQUEST_KEYS, 'invalid_request_fields');
  const canonical = canonicalJson(body);
  if (Buffer.byteLength(canonical, 'utf8') > STRATEGY_CONTRACT.maxRequestBytes) fail('request_too_large', 'Request exceeds 16KiB');
  return {
    body,
    canonical,
    requestDigest: sha256Bytes(Buffer.from(canonical, 'utf8')),
    versionKey: `${input.intentRevision}:${input.briefVersion}:${body.brief_digest}`
  };
}

function enumArray(value, allowed, code, { minItems = 1, maxItems = Number.MAX_SAFE_INTEGER } = {}) {
  if (!Array.isArray(value) || value.length < minItems || value.length > maxItems || new Set(value).size !== value.length) fail(code, 'Enum array violates the closed item-count or uniqueness contract');
  for (const item of value) if (!allowed.has(item)) fail(code, 'Plan or response contains a non-contract enum');
}

function validatePlan(plan, requestBudget) {
  exactKeys(plan, PLAN_KEYS, 'invalid_plan_fields');
  enumArray(plan.query_axes, QUERY_AXES, 'invalid_query_axis', { minItems: 0, maxItems: 5 });
  enumArray(plan.source_classes, SOURCE_CLASSES, 'invalid_source_class', { minItems: 0, maxItems: 4 });
  enumArray(plan.checks, CHECKS, 'invalid_plan_check', { minItems: 5, maxItems: 9 });
  for (const check of REQUIRED_PLAN_CHECKS) {
    if (!plan.checks.includes(check)) fail('required_plan_check_missing', `Plan must include ${check}`);
  }
  enumArray(plan.stop_rules, STOP_RULES, 'invalid_stop_rule', { minItems: 4, maxItems: 4 });
  validateBudget(plan.budget);
  for (const key of BUDGET_KEYS) {
    if (plan.budget[key] > requestBudget[key]) fail('plan_budget_exceeded', 'Plan budget exceeds the accepted request budget');
  }
}

export function validateDecision(response, preparedRequest, nowSeconds) {
  exactKeys(response, RESPONSE_KEYS, 'invalid_response_fields');
  if (response.schema !== 'case.strategy-decision.v1') fail('invalid_response_schema', 'Unexpected response schema');
  if (response.request_id !== preparedRequest.body.request_id || response.intent_revision !== preparedRequest.body.intent_revision || response.brief_version !== preparedRequest.body.brief_version) {
    fail('stale_or_mismatched_decision', 'Decision is not bound to the current request and versions');
  }
  if (response.request_digest !== preparedRequest.requestDigest) fail('request_digest_mismatch', 'Decision request digest does not match');
  uuid(response.decision_id, 'invalid_decision_id');
  if (!DECISION_STATUSES.has(response.status)) fail('invalid_decision_status', 'Unknown decision status');
  integer(response.catalog_revision, 1, 2147483647, 'invalid_catalog_revision');
  timestamp(response.issued_at, 'invalid_issued_at');
  timestamp(response.expires_at, 'invalid_expires_at');
  timestamp(nowSeconds, 'invalid_now');
  if (response.expires_at <= nowSeconds || response.expires_at <= response.issued_at || response.expires_at - response.issued_at > STRATEGY_CONTRACT.expirySeconds) {
    fail('expired_or_invalid_decision', 'Decision is expired or has an invalid issued validity duration');
  }
  if (Math.abs(response.issued_at - nowSeconds) > STRATEGY_CONTRACT.receiveToleranceSeconds) {
    fail('issue_time_outside_receive_window', 'Issued time is outside the 30-second receive tolerance; clock state is unknown');
  }
  enumArray(response.reason_codes, REASON_CODES, 'invalid_reason_code');
  if (response.strategy !== null) {
    exactKeys(response.strategy, ['id', 'version', 'digest'], 'invalid_strategy_fields');
    if (!STRATEGY_ID_PATTERN.test(response.strategy.id)) fail('invalid_strategy_id', 'Invalid strategy ID');
    integer(response.strategy.version, 1, 1000000, 'invalid_strategy_version');
    if (!HEX_64_PATTERN.test(response.strategy.digest)) fail('invalid_strategy_digest', 'Invalid strategy digest');
    // digest belongs to the original catalog template; never recompute it from response.plan.
  }
  if (response.status === 'selected') {
    if (response.strategy === null || response.plan === null) fail('incomplete_selected_decision', 'Selected decision requires strategy and plan');
    if (!response.reason_codes.includes('goal_match')) fail('selected_reason_missing', 'Selected decision requires goal_match');
    validatePlan(response.plan, preparedRequest.body.budget);
  } else {
    if (response.strategy !== null || response.plan !== null) fail('unexpected_nonselected_plan', 'Skipped or unmatched decision must not carry a strategy or plan');
    if (response.status === 'skipped' && !response.reason_codes.some((code) => ['native_short_path', 'capability_limited'].includes(code))) {
      fail('skipped_reason_missing', 'Skipped decision requires native_short_path or capability_limited');
    }
    if (response.status === 'no_match' && !response.reason_codes.includes('no_active_strategy')) {
      fail('no_match_reason_missing', 'No-match decision requires no_active_strategy');
    }
  }
  return response;
}

function timestamp(value, code) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) fail(code, 'UNIX seconds must be a finite non-negative number');
}

function monotonicTimestamp(value) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) fail('invalid_monotonic_clock', 'Monotonic milliseconds must be finite and non-negative');
}

function fallback(prepared, error) {
  return {
    status: 'fallback',
    online_strategy_adopted: false,
    reason_code: error instanceof StrategyClientError ? error.code : 'strategy_unavailable',
    request_id: prepared.body.request_id,
    intent_revision: prepared.body.intent_revision,
    brief_version: prepared.body.brief_version,
    request_digest: prepared.requestDigest
  };
}

async function readResponseTextBounded(response, signal) {
  if (!response || typeof response.text !== 'function') fail('invalid_http_response', 'Host fetch returned no readable response');
  if (response.body && typeof response.body.getReader === 'function') {
    const reader = response.body.getReader();
    const chunks = [];
    let total = 0;
    try {
      while (true) {
        if (signal.aborted) fail('strategy_timeout', 'Strategy response body read was aborted');
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = Buffer.from(value);
        total += chunk.length;
        if (total > STRATEGY_CONTRACT.maxResponseBytes) fail('response_too_large', 'Strategy response body exceeds 64KiB');
        chunks.push(chunk);
      }
    } finally {
      reader.releaseLock();
    }
    try {
      return new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks, total));
    } catch {
      fail('invalid_response_encoding', 'Strategy response body is not valid UTF-8');
    }
  }
  const text = await response.text();
  if (typeof text !== 'string') fail('invalid_http_response', 'Response body did not produce text');
  if (Buffer.byteLength(text, 'utf8') > STRATEGY_CONTRACT.maxResponseBytes) fail('response_too_large', 'Strategy response body exceeds 64KiB');
  return text;
}

function fixedEndpoint(baseUrl, path) {
  if (![STRATEGY_CONTRACT.baseUrl, STRATEGY_CONTRACT.developmentBaseUrl].includes(baseUrl)) {
    fail('unsupported_base_url', 'Only the fixed production URL or the explicit loopback development URL is allowed');
  }
  if (![STRATEGY_CONTRACT.resolvePath, STRATEGY_CONTRACT.feedbackPath].includes(path)) {
    fail('unsupported_path', 'Only the resolve and feedback contract paths are allowed');
  }
  return `${baseUrl}${path}`;
}

export class StrategyClient {
  #fetch;
  #baseUrl;
  #timeoutMs;
  #now;
  #monotonicNow;

  constructor({ fetchImpl = globalThis.fetch, baseUrl = STRATEGY_CONTRACT.baseUrl, timeoutMs = STRATEGY_CONTRACT.timeoutMs, now = () => Date.now() / 1000, monotonicNow = () => performance.now() } = {}) {
    fixedEndpoint(baseUrl, STRATEGY_CONTRACT.resolvePath);
    if (typeof fetchImpl !== 'function') fail('fetch_unavailable', 'No host fetch implementation is available');
    if (typeof now !== 'function' || typeof monotonicNow !== 'function') fail('invalid_clock', 'UTC and monotonic clock functions are required');
    integer(timeoutMs, 1, 3000, 'invalid_timeout');
    this.#fetch = fetchImpl;
    this.#baseUrl = baseUrl;
    this.#timeoutMs = timeoutMs;
    this.#now = now;
    this.#monotonicNow = monotonicNow;
    this.requests = new Map();
    this.versions = new Map();
    this.latestIntentRevision = 0;
    this.latestBriefVersion = 0;
    this.decisions = new Map();
    this.feedback = new Map();
    this.feedbackIds = new Map();
    this.feedbackDecisionIds = new Map();
  }

  trackVersions(prepared) {
    const intentRevision = prepared.body.intent_revision;
    const briefVersion = prepared.body.brief_version;
    if (intentRevision < this.latestIntentRevision || briefVersion < this.latestBriefVersion) {
      fail('stale_intent_or_brief_version', 'A newer intent or brief version has superseded this request');
    }
    this.latestIntentRevision = intentRevision;
    this.latestBriefVersion = briefVersion;
  }

  isCurrentVersions(prepared) {
    return prepared.body.intent_revision === this.latestIntentRevision && prepared.body.brief_version === this.latestBriefVersion;
  }

  async resolve(input) {
    const prepared = buildIntentRequest(input);
    this.trackVersions(prepared);
    if (!NETWORK_MODES.has(input.mode)) {
      return {
        status: 'native_short_path',
        online_strategy_adopted: false,
        request_id: prepared.body.request_id,
        intent_revision: prepared.body.intent_revision,
        brief_version: prepared.body.brief_version,
        request_digest: prepared.requestDigest
      };
    }
    const priorVersion = this.versions.get(prepared.versionKey);
    if (priorVersion && priorVersion !== input.requestId) fail('intent_version_already_resolved', 'Use the original request ID for this effective intent version');
    const prior = this.requests.get(input.requestId);
    if (prior) {
      if (prior.prepared.canonical !== prepared.canonical) fail('request_id_body_conflict', 'The same request ID cannot carry a different body');
      if (prior.outcome.status === 'selected') {
        try {
          return this.getDecisionForUse({ requestId: input.requestId, intentRevision: input.intentRevision, briefVersion: input.briefVersion });
        } catch (error) {
          return fallback(prepared, error);
        }
      }
      return prior.outcome;
    }
    let outcome;
    let receipt = null;
    try {
      const response = await this.postWithRetry(STRATEGY_CONTRACT.resolvePath, prepared.canonical);
      const receivedAtUtc = this.#now();
      const receivedMonotonicMs = this.#monotonicNow();
      monotonicTimestamp(receivedMonotonicMs);
      const decision = validateDecision(response, prepared, receivedAtUtc);
      if (!this.isCurrentVersions(prepared)) fail('stale_intent_or_brief_version', 'A newer intent or brief version superseded the response while it was outstanding');
      outcome = decision;
      if (decision.status === 'selected') {
        const localLifetimeSeconds = Math.min(decision.expires_at - receivedAtUtc, STRATEGY_CONTRACT.expirySeconds);
        receipt = { receivedAtUtc, receivedMonotonicMs, deadlineMonotonicMs: receivedMonotonicMs + localLifetimeSeconds * 1000 };
        this.decisions.set(decision.decision_id, { decision, prepared, receipt });
      }
    } catch (error) {
      outcome = fallback(prepared, error);
    }
    this.requests.set(input.requestId, { prepared, outcome, receipt });
    if (outcome.reason_code !== 'catalog_changed') this.versions.set(prepared.versionKey, input.requestId);
    return outcome;
  }

  getDecisionForUse(input) {
    exactKeys(input, ['requestId', 'intentRevision', 'briefVersion'], 'invalid_decision_use_input');
    uuid(input.requestId, 'invalid_request_id');
    integer(input.intentRevision, 1, 1000000, 'invalid_intent_revision');
    integer(input.briefVersion, 1, 1000000, 'invalid_brief_version');
    const request = this.requests.get(input.requestId);
    if (!request) fail('selected_decision_missing', 'No decision exists for this request');
    const prepared = request.prepared;
    if (prepared.body.intent_revision !== input.intentRevision || prepared.body.brief_version !== input.briefVersion || !this.isCurrentVersions(prepared)) {
      fail('stale_intent_or_brief_version', 'The decision does not match the current intent and brief versions');
    }
    if (request.outcome.status !== 'selected' || !request.receipt) fail('selected_decision_missing', 'No accepted selected decision exists for this request');
    const currentUtc = this.#now();
    const currentMonotonicMs = this.#monotonicNow();
    timestamp(currentUtc, 'invalid_now');
    monotonicTimestamp(currentMonotonicMs);
    if (currentUtc >= request.outcome.expires_at || currentMonotonicMs >= request.receipt.deadlineMonotonicMs) {
      fail('decision_expired', 'The fixed local monotonic deadline or server expiry has passed');
    }
    return request.outcome;
  }

  async postWithRetry(path, canonical) {
    fixedEndpoint(this.#baseUrl, path);
    let lastError;
    for (let attempt = 0; attempt < 2; attempt += 1) {
      try {
        return await this.postOnce(path, canonical);
      } catch (error) {
        lastError = error;
        if (error instanceof StrategyClientError && ['http_client_error', 'catalog_changed', 'invalid_response_json', 'redirect_rejected', 'response_too_large'].includes(error.code)) throw error;
      }
    }
    throw lastError;
  }

  async postOnce(path, canonical) {
    const url = fixedEndpoint(this.#baseUrl, path);
    if (typeof canonical !== 'string' || Buffer.byteLength(canonical, 'utf8') > STRATEGY_CONTRACT.maxRequestBytes) {
      fail('request_too_large', 'Canonical request body must be a string of at most 16KiB');
    }
    const controller = new AbortController();
    let timer;
    const timeout = new Promise((_, reject) => {
      timer = setTimeout(() => {
        controller.abort();
        reject(new StrategyClientError('strategy_timeout', 'Strategy fetch, body read, or parsing exceeded the deadline'));
      }, this.#timeoutMs);
    });
    const operation = (async () => {
      let response;
      try {
        response = await this.#fetch(url, {
          method: 'POST',
          headers: { 'content-type': 'application/json; charset=utf-8', 'accept': 'application/json' },
          body: canonical,
          redirect: 'error',
          signal: controller.signal
        });
      } catch (error) {
        if (error?.name === 'AbortError' || error?.name === 'TimeoutError') throw new StrategyClientError('strategy_timeout', 'Strategy request timed out');
        throw new StrategyClientError('strategy_transport_error', 'Strategy transport failed');
      }
      if (!response || typeof response.status !== 'number') throw new StrategyClientError('invalid_http_response', 'Host fetch returned no valid response');
      if (response.status >= 300 && response.status < 400) throw new StrategyClientError('redirect_rejected', 'Redirects are not accepted');
      const text = await readResponseTextBounded(response, controller.signal);
      let payload;
      try {
        payload = parseJsonStrict(text, STRATEGY_CONTRACT.maxResponseBytes, { allowFiniteNumbers: true });
      } catch {
        throw new StrategyClientError('invalid_response_json', 'Strategy endpoint returned invalid or non-closed JSON');
      }
      // Current service uses {error: code}; earlier fixtures used {code: code}.
      // Accept only one closed key, never free-text errors or conflicting envelopes.
      const errorKey = isObject(payload) && Object.keys(payload).length === 1 ? Object.keys(payload)[0] : null;
      const serverCode = ['error', 'code'].includes(errorKey) ? payload[errorKey] : null;
      if (response.status === 409 && serverCode === 'catalog_changed') throw new StrategyClientError('catalog_changed', 'Catalog changed; a new request ID is required');
      if (response.status >= 400 && response.status < 500) {
        const error = new StrategyClientError('http_client_error', 'Strategy endpoint rejected the request');
        const allowed = ['decision_unrecognized', 'feedback_conflict', 'invalid_feedback', 'feedback_exceeds_decision_budget'];
        if (path === STRATEGY_CONTRACT.feedbackPath && allowed.includes(serverCode)) error.serverCode = serverCode;
        throw error;
      }
      if (response.status < 200 || response.status >= 300) throw new StrategyClientError('http_server_error', 'Strategy endpoint returned a server error');
      return payload;
    })();
    try {
      return await Promise.race([operation, timeout]);
    } finally {
      clearTimeout(timer);
      controller.abort();
    }
  }

  async sendFeedback(input) {
    exactKeys(input, ['decisionId', 'feedbackId', 'consent', 'metrics'], 'invalid_feedback_input');
    if (input.consent !== true) return { status: 'not_uploaded', online_feedback_sent: false };
    uuid(input.feedbackId, 'invalid_feedback_id');
    uuid(input.decisionId, 'invalid_decision_id');
    const binding = this.decisions.get(input.decisionId);
    if (!binding) fail('decision_binding_missing', 'Feedback requires a selected decision actually issued to this client');
    if (this.feedback.has(input.decisionId)) fail('feedback_already_sent', 'Only one feedback is allowed per decision');
    validateMetrics(input.metrics, binding.decision.plan);
    const body = {
      schema: 'case.feedback.v1',
      feedback_id: input.feedbackId,
      decision_id: input.decisionId,
      request_digest: binding.prepared.requestDigest,
      consent: true,
      metrics: input.metrics
    };
    exactKeys(body, FEEDBACK_KEYS, 'invalid_feedback_fields');
    const canonical = canonicalJson(body);
    const priorFeedback = this.feedbackIds.get(input.feedbackId);
    if (priorFeedback && priorFeedback !== canonical) fail('feedback_id_body_conflict', 'The same feedback ID cannot carry a different body');
    this.reserveFeedback(input.decisionId, input.feedbackId, canonical);
    // Never silently repeat a state-changing request after an unknown outcome.
    const result = validateFeedbackResult(await this.postOnce(STRATEGY_CONTRACT.feedbackPath, canonical));
    this.feedback.set(input.decisionId, { canonical, result });
    this.feedbackIds.set(input.feedbackId, canonical);
    return result;
  }

  reserveFeedback(decisionId, feedbackId, canonical) {
    const priorBody = this.feedbackIds.get(feedbackId);
    if (priorBody && priorBody !== canonical) fail('feedback_id_body_conflict', 'Keep the original feedback ID and body after an unknown outcome');
    const priorId = this.feedbackDecisionIds.get(decisionId);
    if (priorId && priorId !== feedbackId) fail('feedback_decision_id_conflict', 'This decision already has a prepared feedback ID');
    this.feedbackIds.set(feedbackId, canonical);
    this.feedbackDecisionIds.set(decisionId, feedbackId);
  }

  exportFeedbackBinding(decisionId) {
    uuid(decisionId, 'invalid_decision_id');
    const binding = this.decisions.get(decisionId);
    if (!binding) fail('decision_binding_missing', 'No selected decision received by this client');
    const issued = Math.floor(binding.decision.issued_at * 1000);
    return validateFeedbackBinding({
      schema: 'case.feedback-binding.v1', base_url: this.#baseUrl,
      decision_id: decisionId, request_digest: binding.prepared.requestDigest,
      issued_at_ms: issued, feedback_until_ms: issued + 86400000,
      budget: { ...binding.decision.plan.budget }
    });
  }

  async sendPreparedFeedback(record, { consent = false } = {}) {
    const copy = validateFeedbackRecord(record);
    if (consent !== true) return { ...copy, send_attempted: false };
    if (copy.binding.base_url !== this.#baseUrl) fail('feedback_endpoint_mismatch', 'Feedback may only return to its issuing endpoint');
    if (!['prepared', 'outcome_unknown'].includes(copy.status)) return { ...copy, send_attempted: false };
    const now = this.#now() * 1000;
    if (!Number.isFinite(now) || now < copy.binding.issued_at_ms - 30000) fail('invalid_feedback_clock', 'Clock precedes the issuing decision');
    if (now >= copy.binding.feedback_until_ms) return { ...copy, status: 'expired', result_code: 'expired', send_attempted: false };
    const body = feedbackBody(copy);
    this.reserveFeedback(copy.binding.decision_id, copy.feedback_id, canonicalJson(body));
    try {
      const result = validateFeedbackResult(await this.postOnce(STRATEGY_CONTRACT.feedbackPath, canonicalJson(body)));
      this.feedback.set(copy.binding.decision_id, { canonical: canonicalJson(body), result });
      return { ...copy, status: result.status, result_code: result.status, send_attempted: true };
    } catch (error) {
      const rejected = ['decision_unrecognized', 'feedback_conflict', 'invalid_feedback', 'feedback_exceeds_decision_budget'].includes(error.serverCode);
      return { ...copy, status: rejected ? 'rejected' : 'outcome_unknown', result_code: rejected ? error.serverCode : 'outcome_unknown', send_attempted: true };
    }
  }
}

function validateFeedbackResult(result) {
  if (result?.status === 'accepted') {
    exactKeys(result, ['status', 'provenance'], 'invalid_feedback_receipt');
    if (result.provenance !== 'anonymous_client_report_unverified') fail('invalid_feedback_receipt', 'Unknown feedback provenance');
  } else if (result?.status === 'duplicate') {
    exactKeys(result, ['status'], 'invalid_feedback_receipt');
  } else fail('invalid_feedback_receipt', 'A valid accepted/duplicate receipt is required');
  return result;
}

export function validateFeedbackBinding(value) {
  exactKeys(value, ['schema','base_url','decision_id','request_digest','issued_at_ms','feedback_until_ms','budget'], 'invalid_feedback_binding');
  if (value.schema !== 'case.feedback-binding.v1') fail('invalid_feedback_binding', 'Unknown binding schema');
  fixedEndpoint(value.base_url, STRATEGY_CONTRACT.feedbackPath);
  uuid(value.decision_id, 'invalid_decision_id');
  if (typeof value.request_digest !== 'string' || !HEX_64_PATTERN.test(value.request_digest)) fail('invalid_feedback_binding', 'Invalid request digest');
  integer(value.issued_at_ms, 0, Number.MAX_SAFE_INTEGER - 86400000, 'invalid_feedback_binding');
  if (value.feedback_until_ms !== value.issued_at_ms + 86400000) fail('invalid_feedback_binding', 'Feedback window must not be extended');
  validateBudget(value.budget);
  return JSON.parse(canonicalJson(value));
}

function feedbackBody(record) {
  return { schema: 'case.feedback.v1', feedback_id: record.feedback_id,
    decision_id: record.binding.decision_id, request_digest: record.binding.request_digest,
    consent: true, metrics: record.metrics };
}

function validatePortableMetrics(metrics, budget) {
  // Reuse the existing wire contract; unknown required counters must not become zero.
  validateMetrics(metrics, { query_axes: [], source_classes: [], checks: [], stop_rules: [], budget });
}

export function prepareFeedback(binding, metrics, feedbackId = randomUUID()) {
  const checked = validateFeedbackBinding(binding);
  uuid(feedbackId, 'invalid_feedback_id');
  validatePortableMetrics(metrics, checked.budget);
  const record = { schema: 'case.feedback-record.v1', binding: checked, feedback_id: feedbackId,
    metrics: JSON.parse(canonicalJson(metrics)), status: 'prepared', result_code: null, body_sha256: '' };
  record.body_sha256 = sha256Bytes(canonicalJson(feedbackBody(record)));
  return record;
}

export function validateFeedbackRecord(record) {
  exactKeys(record, ['schema','binding','feedback_id','metrics','status','result_code','body_sha256'], 'invalid_feedback_record');
  if (record.schema !== 'case.feedback-record.v1') fail('invalid_feedback_record', 'Unknown feedback schema');
  const expected = prepareFeedback(record.binding, record.metrics, record.feedback_id);
  const codes = { prepared: [null], outcome_unknown: ['outcome_unknown'], accepted: ['accepted'], duplicate: ['duplicate'],
    withdrawn: ['withdrawn_locally'], expired: ['expired'], rejected: ['decision_unrecognized','feedback_conflict','invalid_feedback','feedback_exceeds_decision_budget'] };
  if (!Object.hasOwn(codes, record.status) || !codes[record.status].includes(record.result_code) || record.body_sha256 !== expected.body_sha256) fail('invalid_feedback_record', 'Feedback status or original body digest changed');
  return JSON.parse(canonicalJson(record));
}

export function withdrawFeedback(record) {
  const copy = validateFeedbackRecord(record);
  if (['accepted','duplicate'].includes(copy.status)) fail('feedback_already_recorded', 'Local withdrawal cannot delete an accepted server aggregate');
  return { ...copy, status: 'withdrawn', result_code: 'withdrawn_locally' };
}

function validateMetrics(metrics, issuedPlan) {
  exactKeys(metrics, METRIC_KEYS, 'invalid_feedback_metrics');
  exactKeys(issuedPlan, PLAN_KEYS, 'invalid_issued_plan');
  const bounded = {
    queries: [0, 12], reads: [0, 20], cases_checked: [0, 6], cases_usable: [0, 6],
    critical_fields_total: [0, 100], critical_fields_supported: [0, 100],
    transfer_conditions_total: [0, 100], transfer_conditions_met: [0, 100], transfer_conditions_unknown: [0, 100]
  };
  for (const [key, [min, max]] of Object.entries(bounded)) integer(metrics[key], min, max, 'invalid_feedback_metric');
  if (metrics.cases_usable > metrics.cases_checked || metrics.critical_fields_supported > metrics.critical_fields_total || metrics.transfer_conditions_met + metrics.transfer_conditions_unknown > metrics.transfer_conditions_total) {
    fail('inconsistent_feedback_metrics', 'Feedback metric subsets exceed their totals');
  }
  for (const [metric, budget] of [['queries', 'max_queries'], ['reads', 'max_reads'], ['cases_checked', 'max_cases']]) {
    if (metrics[metric] > issuedPlan.budget[budget]) fail('feedback_plan_budget_exceeded', `${metric} exceeds the exact issued plan budget`);
  }
  if (typeof metrics.counterevidence_checked !== 'boolean') fail('invalid_feedback_metric', 'counterevidence_checked must be boolean');
  if (metrics.elapsed_ms !== null) integer(metrics.elapsed_ms, 0, 3600000, 'invalid_elapsed_ms');
  if (metrics.user_relevance !== null && !['relevant', 'partial', 'not_relevant'].includes(metrics.user_relevance)) fail('invalid_user_relevance', 'Invalid user relevance');
  if (metrics.adoption !== null && !['reported_planned', 'reported_started', 'reported_completed'].includes(metrics.adoption)) fail('invalid_adoption', 'Invalid adoption value');
}

export function createStrategyClient(options) {
  return new StrategyClient(options);
}

export function createRequestInput(overrides) {
  if (!isObject(overrides)) fail('invalid_local_request_fields', 'Request input overrides are required');
  return { requestId: randomUUID(), ...overrides };
}
