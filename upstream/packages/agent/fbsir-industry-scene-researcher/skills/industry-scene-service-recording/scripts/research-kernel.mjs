import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { checkClaimsRelations, assessDeliveryRecords } from './claims-lite.mjs';
import { renderSemanticMarkdown, RESEARCH_CSS } from './research-presentation.mjs';

// Pure data processing after reading bundled schema files. No network,
// LLM, media observation, file writes, services, or factual-truth certification.
export const EVIDENCE_LABELS = Object.freeze(['source_fact', 'company_claim',
  'independent_observation', 'user_statement', 'inference', 'hypothesis', 'unknown']);
export const DIMENSIONS = Object.freeze({
  new_business_form: '新业态', new_model: '新模式', new_value_space: '新价值空间',
  new_scenario: '新场景', new_factor: '新要素', new_organization: '新组织形态', new_tool: '新工具'
});
const schemaNames = ['common.schema.json', 'research-objects.schema.json',
  'material-observation.schema.json', 'continuation.schema.json', 'claims-lite.schema.json',
  'track-research.schema.json'];
const schemas = Object.fromEntries(schemaNames.map(name =>
  [name, JSON.parse(readFileSync(new URL('../schemas/' + name, import.meta.url), 'utf8'))]));
const plain = v => v !== null && typeof v === 'object' && !Array.isArray(v) &&
  [Object.prototype, null].includes(Object.getPrototypeOf(v));
const nonempty = v => typeof v === 'string' && v.trim().length > 0;
const sha = v => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const error = (path, code, message) => ({ path, code, message });
function parsedHttpHost(value) {
  if (!nonempty(value)) return null;
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) return null;
    return url.hostname.toLowerCase().replace(/\.$/, '');
  } catch { return null; }
}
function hostAllowed(host, rules) {
  return rules.some(rule => {
    if (!nonempty(rule)) return false;
    const wildcard = rule.startsWith('*.');
    const raw = wildcard ? rule.slice(2) : rule;
    if (/[/:?#@]/.test(raw)) return false;
    const normalized = parsedHttpHost('https://' + raw);
    if (!normalized) return false;
    return wildcard ? host.endsWith('.' + normalized) && host !== normalized : host === normalized;
  });
}
export class KernelInputError extends Error {
  constructor(errors) {
    super(errors.map(e => e.path + ': ' + e.message).join('; '));
    this.name = 'KernelInputError'; this.errors = errors;
  }
}
function reject(code, message, path = '$') { throw new KernelInputError([error(path, code, message)]); }
function assertJSON(value) {
  let nodes = 0; const active = new Set();
  function walk(v, depth, path) {
    if (++nodes > 100000 || depth > 64) reject('input_budget_exceeded', 'JSON processing budget exceeded', path);
    if (v === null || typeof v === 'string' || typeof v === 'boolean') return;
    if (typeof v === 'number') {
      if (!Number.isFinite(v)) reject('non_json_number', 'Numbers must be finite', path);
      return;
    }
    if (!Array.isArray(v) && !plain(v)) reject('non_json_value', 'Only plain JSON data is accepted', path);
    if (Array.isArray(v)) for (let i = 0; i < v.length; i++)
      if (!Object.hasOwn(v, i)) reject('sparse_json_array', 'Sparse arrays are not JSON arrays', path);
    if (active.has(v)) reject('cyclic_input', 'Cyclic data is not JSON', path);
    active.add(v);
    for (const [k, child] of Object.entries(v)) walk(child, depth + 1, path + '/' + k);
    active.delete(v);
  }
  walk(value, 0, '$');
}
export function canonicalJSON(value) {
  assertJSON(value);
  const sort = v => Array.isArray(v) ? v.map(sort) : plain(v) ?
    Object.fromEntries(Object.keys(v).sort().map(k => [k, sort(v[k])])) : v;
  return JSON.stringify(sort(value));
}
const hash = value => createHash('sha256').update(canonicalJSON(value)).digest('hex');
const clone = value => JSON.parse(canonicalJSON(value));

// Executes the standard 2020-12 keywords used by these contracts. Unsupported
// validation keywords fail closed; this is not an all-vocabulary Schema engine.
const keywords = new Set(['$schema', '$id', '$ref', '$defs', 'title', 'description',
  '$comment', 'type', 'const', 'enum', 'required', 'properties', 'additionalProperties',
  'items', 'prefixItems', 'minItems', 'maxItems', 'uniqueItems', 'minLength', 'maxLength',
  'pattern', 'format', 'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum',
  'minProperties', 'maxProperties', 'anyOf', 'oneOf', 'allOf', 'not', 'if', 'then', 'else']);
function schemaErrors() {
  const errors = [];
  function visit(node, path) {
    if (typeof node === 'boolean') return;
    if (!plain(node)) { errors.push(error(path, 'schema_invalid', 'Invalid schema object')); return; }
    for (const key of Object.keys(node)) if (!keywords.has(key))
      errors.push(error(path + '/' + key, 'schema_keyword_unsupported', 'Unsupported schema keyword'));
    for (const key of ['properties', '$defs']) if (Object.hasOwn(node, key)) {
      if (!plain(node[key])) { errors.push(error(path + '/' + key, 'schema_map_invalid', 'Schema maps must be plain objects')); continue; }
      for (const [name, child] of Object.entries(node[key])) visit(child, path + '/' + key + '/' + name);
    }
    for (const key of ['items', 'additionalProperties', 'not', 'if', 'then', 'else'])
      if (node[key] !== undefined) visit(node[key], path + '/' + key);
    for (const key of ['prefixItems', 'anyOf', 'oneOf', 'allOf'])
      for (const [i, child] of (node[key] || []).entries()) visit(child, path + '/' + key + '/' + i);
  }
  for (const [name, schema] of Object.entries(schemas)) {
    if (schema.$schema !== 'https://json-schema.org/draft/2020-12/schema')
      errors.push(error(name, 'schema_draft_invalid', 'JSON Schema 2020-12 required'));
    visit(schema, name);
  }
  const main = schemas['research-objects.schema.json'];
  const required = ['schemaVersion', 'researchBrief', 'sources', 'observations', 'claims', 'cases', 'analysis', 'outputs', 'continuation'];
  const mainProperties = plain(main.properties) ? main.properties : {};
  if (main.additionalProperties !== false || required.some(k => !main.required?.includes(k) || !Object.hasOwn(mainProperties, k)))
    errors.push(error('research-objects.schema.json', 'schema_contract_weakened', 'Incomplete bundle contract'));
  if (canonicalJSON(schemas['common.schema.json'].$defs?.evidenceStatus?.enum || []) !== canonicalJSON(EVIDENCE_LABELS))
    errors.push(error('common.schema.json', 'evidence_labels_drift', 'The seven Skill labels must be preserved'));
  for (const name of ['source', 'claim', 'case', 'analysis']) {
    const definitions = plain(main.$defs) ? main.$defs : {};
    const d = Object.hasOwn(definitions, name) ? definitions[name] : undefined;
    if (!d || d.additionalProperties !== false || !d.required?.length || !Object.keys(d.properties || {}).length)
      errors.push(error('$defs/' + name, 'schema_contract_weakened', 'Incomplete required object'));
  }
  return errors;
}
const contractErrors = schemaErrors();
function resolveRef(reference, documentName) {
  if (typeof reference !== 'string' || (reference.match(/#/g) || []).length > 1)
    reject('schema_ref_unresolved', 'Malformed local schema reference');
  const [file, pointer] = reference.split('#');
  const name = !file ? documentName : Object.hasOwn(schemas, file) ? file :
    Object.keys(schemas).find(key => schemas[key].$id === file);
  if (!name) reject('schema_ref_unresolved', 'Only bundled schema references are allowed');
  let node = schemas[name];
  if (pointer) {
    if (!pointer.startsWith('/')) reject('schema_ref_unresolved', 'Only JSON Pointer fragments are allowed');
    for (const part of pointer.slice(1).split('/')) {
      const token = part.replaceAll('~1', '/').replaceAll('~0', '~');
      if ((!plain(node) && !Array.isArray(node)) || !Object.hasOwn(node, token))
        reject('schema_ref_unresolved', 'Reference path is not an own schema member: ' + reference);
      node = node[token];
    }
  }
  if (node === undefined) reject('schema_ref_unresolved', reference);
  if (typeof node !== 'boolean' && !plain(node)) reject('schema_ref_unresolved', 'Reference target is not a schema node');
  return { node, name };
}

function validDateTime(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-](\d{2}):(\d{2}))$/.exec(value);
  if (!match) return false;
  const year = Number(match[1]), month = Number(match[2]), day = Number(match[3]);
  const hour = Number(match[4]), minute = Number(match[5]), second = Number(match[6]);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (month < 1 || month > 12 || day < 1 || day > days[month - 1] || hour > 23 || minute > 59 || second > 59) return false;
  if (match[9] !== undefined && (Number(match[9]) > 23 || Number(match[10]) > 59)) return false;
  return Number.isFinite(Date.parse(value));
}
function matchesType(v, type) {
  if (type === 'null') return v === null;
  if (type === 'object') return plain(v);
  if (type === 'array') return Array.isArray(v);
  if (type === 'integer') return Number.isInteger(v);
  if (type === 'number') return typeof v === 'number' && Number.isFinite(v);
  return typeof v === type;
}
function evaluateSchema(value, schema, documentName, path, depth = 0) {
  if (depth > 128) return [error(path, 'schema_depth_exceeded', 'Schema nesting budget exceeded')];
  if (schema === true) return [];
  if (schema === false) return [error(path, 'schema_false', 'Value not allowed here')];
  const errors = [], add = (code, message) => errors.push(error(path, code, message));
  const run = child => evaluateSchema(value, child, documentName, path, depth + 1);
    if (Object.hasOwn(schema, '$ref') && schema.$ref) {
    const target = resolveRef(schema.$ref, documentName);
    errors.push(...evaluateSchema(value, target.node, target.name, path, depth + 1));
  }
  if (schema.type && !(Array.isArray(schema.type) ? schema.type : [schema.type]).some(t => matchesType(value, t))) {
    add('schema_type', 'Expected ' + JSON.stringify(schema.type)); return errors;
  }
  if (Object.hasOwn(schema, 'const') && canonicalJSON(value) !== canonicalJSON(schema.const)) add('schema_const', 'Required constant differs');
  if (schema.enum && !schema.enum.some(v => canonicalJSON(v) === canonicalJSON(value))) add('schema_enum', 'Value outside enumeration');
  if (schema.anyOf && !schema.anyOf.some(child => run(child).length === 0)) add('schema_any_of', 'No allowed alternative matches');
  if (schema.oneOf && schema.oneOf.filter(child => run(child).length === 0).length !== 1) add('schema_one_of', 'Exactly one alternative required');
  for (const child of schema.allOf || []) errors.push(...run(child));
  if (schema.not && run(schema.not).length === 0) add('schema_not', 'Forbidden value');
  if (schema.if) errors.push(...run(run(schema.if).length === 0 ? schema.then ?? true : schema.else ?? true));
  if (typeof value === 'string') {
    const length = [...value].length;
    if (schema.minLength !== undefined && length < schema.minLength) add('schema_min_length', 'String too short');
    if (schema.maxLength !== undefined && length > schema.maxLength) add('schema_max_length', 'String too long');
    if (schema.pattern && !new RegExp(schema.pattern, 'u').test(value)) add('schema_pattern', 'Pattern does not match');
    if (schema.format === 'date-time' && !validDateTime(value))
      add('schema_format', 'Explicit ISO date-time required');
    if (schema.format === 'date' && (!/^\d{4}-\d{2}-\d{2}$/.test(value) || !Number.isFinite(Date.parse(value)) || new Date(value + 'T00:00:00Z').toISOString().slice(0,10) !== value))
      add('schema_format', 'Valid calendar date required');
  }
  if (typeof value === 'number') for (const [key, fails] of [
    ['minimum', x => value < x], ['maximum', x => value > x],
    ['exclusiveMinimum', x => value <= x], ['exclusiveMaximum', x => value >= x]
  ]) if (schema[key] !== undefined && fails(schema[key])) add('schema_' + key, 'Number outside bound');
  if (Array.isArray(value)) {
    if (schema.minItems !== undefined && value.length < schema.minItems) add('schema_min_items', 'Array too short');
    if (schema.maxItems !== undefined && value.length > schema.maxItems) add('schema_max_items', 'Array too long');
    if (schema.uniqueItems && new Set(value.map(canonicalJSON)).size !== value.length) add('schema_unique_items', 'Duplicate array item');
    value.forEach((item, i) => {
      const child = Array.isArray(schema.prefixItems) && Object.hasOwn(schema.prefixItems, i) ? schema.prefixItems[i] : schema.items;
      if (child !== undefined) errors.push(...evaluateSchema(item, child, documentName, path + '/' + i, depth + 1));
    });
  }
  if (plain(value)) {
    for (const key of schema.required || []) if (!Object.hasOwn(value, key)) add('schema_required', 'Missing property: ' + key);
    for (const [key, child] of Object.entries(value)) {
      const properties = plain(schema.properties) ? schema.properties : {};
      const definition = Object.hasOwn(properties, key) ? properties[key] : schema.additionalProperties;
      if (definition !== undefined) errors.push(...evaluateSchema(child, definition, documentName, path + '/' + key, depth + 1));
    }
    if (schema.minProperties !== undefined && Object.keys(value).length < schema.minProperties) add('schema_min_properties', 'Too few properties');
    if (schema.maxProperties !== undefined && Object.keys(value).length > schema.maxProperties) add('schema_max_properties', 'Too many properties');
  }
  return errors.slice(0, 200);
}
export function validateSchema(value, schemaName = 'research-objects.schema.json', definition = null) {
  try {
    assertJSON(value);
    if (contractErrors.length) return { valid: false, errors: clone(contractErrors) };
    if (!Object.hasOwn(schemas, schemaName)) reject('schema_not_bundled', 'Unknown schema name');
    const document = schemas[schemaName];
    const definitions = plain(document.$defs) ? document.$defs : {};
    const root = definition ? (Object.hasOwn(definitions, definition) ? definitions[definition] : undefined) : document;
    if (root === undefined) reject('schema_definition_missing', 'Unknown schema definition');
    const errors = evaluateSchema(value, root, schemaName, '$');
    return { valid: errors.length === 0, errors };
  } catch (failure) {
    return { valid: false, errors: failure.errors || [error('$', 'validation_error', failure.message)] };
  }
}
function requireValid(value, name, definition) {
  const result = validateSchema(value, name, definition);
  if (!result.valid) throw new KernelInputError(result.errors);
}
export function coverageUnion(ranges) {
  if (!Array.isArray(ranges)) reject('ranges_not_array', 'Ranges must be an array');
  const sorted = ranges.map((r, i) => {
    if (!Array.isArray(r) || r.length !== 2 || r.some(n => typeof n !== 'number' || !Number.isFinite(n)) || r[0] < 0 || r[1] <= r[0])
      reject('range_invalid', 'Finite nonnegative [start,end) bounds with end > start required', '$/' + i);
    return [...r];
  }).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const merged = [];
  for (const r of sorted) {
    const last = merged.at(-1);
    if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1]);
    else merged.push(r);
  }
  return merged;
}
export function planMaterialBatches(input) {
  requireValid(input, 'common.schema.json', 'batchPlanningInput');
  const seen = new Set(), available = [], unknownCoverage = [];
  for (const unit of input.contentUnits) {
    if (seen.has(unit.id)) reject('batch_content_unit_duplicate', 'Content unit IDs must be unique');
    seen.add(unit.id);
    if (unit.state === 'available') {
      if (!unit.range) reject('batch_content_range_missing', 'Available content units need an observed range');
      if (!nonempty(unit.readReceiptRef) || !sha(unit.contentSha256))
        reject('batch_content_read_receipt_missing', 'Available content units need an observed read receipt reference and content digest');
      const [start, end] = unit.range;
      if (end <= start || input.knownTotal !== null && end > input.knownTotal)
        reject('batch_content_range_invalid', 'Content ranges must be positive and within the known source boundary');
      if (input.unit !== 'seconds' && (!Number.isInteger(start) || !Number.isInteger(end)))
        reject('batch_content_range_fractional', 'Discrete units need integer range boundaries');
      available.push(clone(unit));
    } else {
      if (unit.readReceiptRef !== null || unit.contentSha256 !== null)
        reject('batch_unavailable_has_read_receipt', 'Unavailable content units cannot claim a successful read receipt');
      unknownCoverage.push(unit.id + ': ' + (unit.unknowns.join('; ') || unit.state));
    }
  }
  const batches = [];
  for (let index = 0; index < available.length; index += input.maxUnitsPerBatch) {
    const units = available.slice(index, index + input.maxUnitsPerBatch);
    batches.push({
      id: 'batch-' + String(batches.length + 1).padStart(3, '0'),
      ranges: coverageUnion(units.map(unit => unit.range)),
      status: 'planned',
      observationIds: [],
      unknowns: []
    });
  }
  const output = {
    id: input.id, sourceId: input.sourceId, sourceVersion: input.sourceVersion,
    purpose: input.purpose, knownTotal: input.knownTotal, unit: input.unit,
    status: 'planned', batches, coverageUnion: [], unknownCoverage,
    nextBatch: batches[0]?.id ?? null
  };
  requireValid(output, 'common.schema.json', 'batchPlan');
  return output;
}
const rangeAmount = ranges => ranges.reduce((sum, r) => sum + r[1] - r[0], 0);
function intersection(a, b) {
  const pieces = []; let i = 0, j = 0;
  while (i < a.length && j < b.length) {
    const x = a[i], y = b[j], start = Math.max(x[0], y[0]), end = Math.min(x[1], y[1]);
    if (end > start) pieces.push([start, end]);
    if (x[1] <= y[1]) i++; else j++;
  }
  return coverageUnion(pieces);
}
function kindSupports(kind, representation) {
  if (['synthetic_observation_fixture', 'user_supplied_observation'].includes(kind)) return representation !== 'metadata';
  if (kind === 'native_visual_observation') return representation === 'visual';
  if (kind === 'native_audio_observation') return representation === 'audio';
  if (kind === 'table_extraction') return representation === 'table';
  return ['text_extraction', 'ocr_derivative', 'asr_derivative', 'user_supplied_transcript'].includes(kind) && representation === 'text';
}
export function computeCoverage(scope) {
  assertJSON(scope);
  if (!plain(scope) || !Array.isArray(scope.observations)) reject('coverage_scope_invalid', 'Scope and observations required');
  for (const key of ['sourceId', 'modality', 'unit', 'representation', 'scopeMode', 'totalBasis'])
    if (!nonempty(scope[key])) reject('coverage_scope_missing', 'Missing ' + key);
  for (const key of ['sourceVersion', 'timebase', 'knownTotal'])
    if (!Object.hasOwn(scope, key)) reject('coverage_scope_missing', key + ' must be explicit, including null');
  requireValid(scope.sourceId, 'common.schema.json', 'id');
  requireValid(scope.modality, 'common.schema.json', 'modality');
  for (const key of ['unit', 'representation', 'totalBasis', 'scopeMode']) {
    const allowed = schemas['common.schema.json'].$defs.coverage.properties[key].enum;
    if (!allowed.includes(scope[key])) reject('coverage_scope_invalid', 'Invalid ' + key);
  }
  for (const key of ['sourceVersion', 'timebase'])
    if (scope[key] !== null && !nonempty(scope[key])) reject('coverage_scope_invalid', 'Invalid ' + key);
  if (scope.knownTotal !== null && (typeof scope.knownTotal !== 'number' || !Number.isFinite(scope.knownTotal) || scope.knownTotal < 0))
    reject('coverage_total_invalid', 'knownTotal must be a nonnegative finite number or null');
  if (!['whole_source', 'selected_scope'].includes(scope.scopeMode)) reject('coverage_scope_invalid', 'Unknown scope mode');
  if (scope.totalBasis === 'unknown' && scope.knownTotal !== null) reject('coverage_total_basis_mismatch', 'Unknown total basis must not carry a known total');
  const requested = scope.requestedRanges === null || scope.requestedRanges === undefined ?
    (scope.scopeMode === 'whole_source' && scope.knownTotal > 0 ? [[0, scope.knownTotal]] : null) : coverageUnion(scope.requestedRanges);
  const ignored = [], eligible = [], declared = [];
  for (const [i, observation] of scope.observations.entries()) {
    const c = observation.coverage;
    if (!plain(c)) reject('coverage_record_missing', 'Observation has no coverage', '$/observations/' + i);
    if (!['whole_unit', 'partial_unit', 'point_sample'].includes(c.granularity)) reject('coverage_granularity_invalid', 'Observation granularity is required');
    if (!['observed', 'ambiguous', 'conflicted', 'unsupported', 'not_observed', 'failed', 'invalidated'].includes(observation.status))
      reject('coverage_state_invalid', 'Unknown observation state');
    requireValid(observation.observationKind, 'common.schema.json', 'observationKind');
    if (observation.sourceId !== scope.sourceId || observation.sourceVersion !== scope.sourceVersion ||
        observation.modality !== scope.modality || c.unit !== scope.unit || c.representation !== scope.representation || c.timebase !== scope.timebase)
      reject('coverage_group_mismatch', 'Source/version/modality/unit/representation/timebase groups differ', '$/observations/' + i);
    const ranges = coverageUnion(c.observedRanges);
    if (scope.unit !== 'seconds' && ranges.some(r => r.some(n => !Number.isInteger(n)))) reject('coverage_fractional_unit', 'Discrete coverage units need integer indices');
    if (scope.knownTotal !== null && ranges.some(r => r[1] > scope.knownTotal)) reject('coverage_out_of_bounds', 'Observation exceeds known total');
    declared.push(...ranges);
    let reason = null;
    if (!['observed', 'ambiguous', 'conflicted'].includes(observation.status)) reason = 'observation_not_current';
    else if (!kindSupports(observation.observationKind, scope.representation)) reason = 'representation_not_observed';
    else if (c.granularity === 'partial_unit') reason = 'partial_unit_is_not_a_whole_unit';
    else if (c.granularity === 'point_sample' && scope.unit !== 'frames') reason = 'sampled_points_are_not_intervals';
    if (reason) ignored.push({ observationId: observation.id, reason });
    else eligible.push(...ranges);
  }
  if (requested && scope.knownTotal !== null && requested.some(r => r[1] > scope.knownTotal)) reject('coverage_out_of_bounds', 'Requested range exceeds known total');
  if (scope.unit !== 'seconds' && requested?.some(r => r.some(n => !Number.isInteger(n)))) reject('coverage_fractional_unit', 'Discrete request units need integer indices');
  const merged = coverageUnion(eligible), amount = rangeAmount(requested ? intersection(merged, requested) : merged);
  const requestedAmount = requested ? rangeAmount(requested) : null;
  const complete = requestedAmount !== null && requestedAmount > 0 && amount === requestedAmount && scope.representation !== 'metadata';
  const points = scope.observations.some(o => o.coverage.granularity === 'point_sample');
  const fullRepresentation = complete && scope.scopeMode === 'whole_source' && scope.knownTotal > 0 &&
    ['observed_metadata', 'synthetic_fixture'].includes(scope.totalBasis) && !points &&
    canonicalJSON(requested) === canonicalJSON([[0, scope.knownTotal]]);
  const originalRepresentations = { text_document: 'text', pdf_scan: 'visual', image: 'visual',
    spreadsheet: 'table', slides_web: 'visual', audio: 'audio' };
  const full = fullRepresentation && originalRepresentations[scope.modality] === scope.representation;
  const limitations = [];
  if (scope.knownTotal === null) limitations.push('total_unknown');
  if (scope.totalBasis === 'user_declared') limitations.push('total_only_user_declared');
  if (points) limitations.push('sampled_frames_do_not_prove_continuous_video');
  if (ignored.length) limitations.push('some_observations_not_eligible_for_this_axis');
  if (scope.observations.some(o => o.observationKind === 'synthetic_observation_fixture')) limitations.push('synthetic_observation_descriptions');
  return { sourceId: scope.sourceId, sourceVersion: scope.sourceVersion, modality: scope.modality,
    unit: scope.unit, representation: scope.representation, timebase: scope.timebase,
    knownTotal: scope.knownTotal, requestedRanges: requested, observedRanges: merged,
    declaredRanges: coverageUnion(declared), observedAmount: amount, requestedAmount,
    ratio: requestedAmount > 0 ? amount / requestedAmount : null,
    completeForDeclaredScope: complete, fullRepresentationCovered: fullRepresentation, fullSourceCovered: full,
    coverageStatus: complete ? 'complete_for_declared_scope' : amount > 0 ? 'partial' : points ? 'sampled' : 'not_observed',
    ignoredObservations: ignored, limitations, provesSemanticAccuracy: false, provesRealMediaProcessing: false };
}
export function cacheKey(components) {
  requireValid(components, 'common.schema.json', 'cacheComponents');
  if (!sha(components.sourceContentDigest)) reject('cache_identity_unknown', 'Reliable content identity required');
  return hash(components);
}
function indexById(items, path, errors) {
  const map = new Map();
  for (const [i, item] of items.entries()) {
    if (map.has(item.id)) errors.push(error(path + '/' + i, 'duplicate_id', 'Duplicate ID: ' + item.id));
    map.set(item.id, item);
  }
  return map;
}
function checkCycle(map, field, path, errors) {
  const active = new Set(), done = new Set();
  function visit(id) {
    if (active.has(id)) { errors.push(error(path + '/' + id, 'reference_cycle', 'Dependency cycle')); return; }
    if (done.has(id) || !map.has(id)) return;
    active.add(id);
    const dependency = map.get(id)[field];
    for (const parent of Array.isArray(dependency) ? dependency : dependency ? [dependency] : []) visit(parent);
    active.delete(id); done.add(id);
  }
  for (const id of map.keys()) visit(id);
}
export function validateResearch(bundle) {
  const structural = validateSchema(bundle);
  if (!structural.valid) return structural;
  if (bundle.schemaVersion === 'research.bundle/v1')
    return { valid: false, errors: [error('$/schemaVersion', 'legacy_bundle_read_only', 'Version 1 bundles are retained for read-only archive viewing; review and revalidate before using them as current evidence')],
      warnings: [], hostEvidenceStatus: 'not_run', semanticTruthStatus: 'not_certified_by_schema_validation' };
  const errors = [], warnings = [], add = (p, c, m) => errors.push(error(p, c, m));
  const warn = (p, c, m) => warnings.push(error(p, c, m));
  if (!nonempty(bundle.researchBrief.question)) add('$/researchBrief/question', 'brief_question_missing', 'A template without a user question is not an executable research request');
  const sourcePolicy = bundle.researchBrief.sourcePolicy;
  const allowedMaterialSourceIds = sourcePolicy.userMaterialSourceIds || [];
  for (const source of bundle.sources) if (!Object.hasOwn(source, 'sourceOrigin'))
    add('$/sources/' + source.id, 'source_origin_missing', 'Version 2 research records explicitly classify web, user-material, other, or synthetic origins');
  if (sourcePolicy.mode === 'only' && !sourcePolicy.domains.length && !allowedMaterialSourceIds.length)
    add('$/researchBrief/sourcePolicy', 'source_scope_empty', 'An only-source policy needs explicit domains or allowlisted user materials');
  const sources = indexById(bundle.sources, '$/sources', errors);
  const observations = indexById(bundle.observations, '$/observations', errors);
  const claims = indexById(bundle.claims, '$/claims', errors);
  const cases = indexById(bundle.cases, '$/cases', errors);
  indexById(bundle.outputs, '$/outputs', errors);
  const refs = (values, map, path) => values.forEach(id => {
    if (!map.has(id)) add(path, 'dangling_reference', 'Unknown reference: ' + id);
  });
  for (const s of sources.values()) {
    const p = '$/sources/' + s.id;
    for (const key of ['requestedUrl', 'effectiveUrl'])
      if (s[key] !== null && s[key] !== undefined && !parsedHttpHost(s[key]))
        add(p + '/' + key, 'source_url_invalid', 'Recorded web addresses must be HTTP(S) without embedded credentials');
    if (/^\s*https?:/i.test(s.uriOrLabel) && !parsedHttpHost(s.uriOrLabel))
      add(p + '/uriOrLabel', 'source_url_invalid', 'A source URL cannot contain embedded credentials');
    if (sourcePolicy.mode === 'only') {
      if (s.sourceOrigin === 'user_material') {
        if (!allowedMaterialSourceIds.includes(s.id)) add(p, 'source_material_not_allowlisted', 'User-provided material must appear in the explicit source ID allowlist');
        if (s.effectiveUrl) add(p, 'user_material_has_web_origin', 'A source with an effective web URL must be classified and checked as web material');
      } else if (s.sourceOrigin === 'web') {
        const host = parsedHttpHost(s.effectiveUrl);
        if (!host) add(p, 'source_effective_url_missing', 'A web source under only-source policy needs the final URL actually read');
        else if (!hostAllowed(host, sourcePolicy.domains)) add(p, 'source_domain_outside_scope', 'The final URL host is outside the allowed source domains');
        if (s.requestedUrl && !parsedHttpHost(s.requestedUrl)) add(p, 'source_requested_url_invalid', 'Requested URL must be HTTP(S) when recorded');
      } else add(p, 'source_origin_unverified', 'Only web sources with an observed final URL or explicitly allowlisted user material are permitted');
    }
    if (s.derivedFrom) {
      refs([s.derivedFrom], sources, p + '/derivedFrom');
      if (sources.get(s.derivedFrom)?.sourceFamily !== s.sourceFamily) add(p, 'source_family_mismatch', 'Derivative must retain its source family');
    }
    if (s.identityBasis === 'unknown' && s.contentDigest !== null) add(p, 'unknown_identity_has_digest', 'Unknown identity cannot carry a factual digest');
    if (['observed_bytes', 'synthetic_fixture'].includes(s.identityBasis) && !sha(s.contentDigest)) add(p, 'source_digest_required', 'Content identity requires its digest');
    if (s.materialRole === 'synthetic_example' && s.identityBasis !== 'synthetic_fixture') add(p, 'synthetic_identity_required', 'Synthetic material must keep synthetic identity');
  }
  checkCycle(sources, 'derivedFrom', '$/sources', errors);
  for (const o of observations.values()) {
    const p = '$/observations/' + o.id, s = sources.get(o.sourceId);
    refs([o.sourceId], sources, p + '/sourceId'); refs(o.derivedFromObservationIds, observations, p + '/derivedFromObservationIds');
    if (!s) continue;
    if (s.materialRole !== o.materialRole) add(p, 'material_role_mismatch', 'Source and observation roles differ');
    if (o.status !== 'invalidated' && (s.version !== o.sourceVersion || s.contentDigest !== o.sourceIdentity))
      add(p, 'observation_source_drift', 'Observation is not bound to current source identity/version');
    if (s.materialRole === 'synthetic_example' && o.observationKind !== 'synthetic_observation_fixture')
      add(p, 'synthetic_observation_upgrade', 'Synthetic descriptions cannot become native observations');
    if (['not_observed', 'unsupported', 'failed'].includes(o.status) && o.coverage.observedRanges.length)
      add(p, 'unobserved_has_ranges', 'Unobserved or failed entries cannot claim observed ranges');
    for (const a of o.anchors) {
      if (a.rectangle && (!a.dimensions || a.rectangle.x + a.rectangle.width > a.dimensions.width || a.rectangle.y + a.rectangle.height > a.dimensions.height))
        add(p + '/anchors', 'rectangle_out_of_bounds', 'Rectangle must fit the actual declared bitmap dimensions');
      if ((a.start === null) !== (a.end === null) || a.start !== null && a.end <= a.start)
        add(p + '/anchors', 'time_anchor_invalid', 'Valid start/end pair required');
    }
    if (o.tabularContext) for (const cell of o.tabularContext.cells) {
      if (cell.calculatedValue !== null && (cell.calculationState !== 'calculated' || !nonempty(cell.calculationEvidenceRef)))
        add(p + '/tabularContext', 'calculation_evidence_missing', 'Calculated values require an explicit calculation record');
      if (cell.calculationState === 'calculated' && !nonempty(cell.calculationEvidenceRef))
        add(p + '/tabularContext', 'calculation_evidence_missing', 'Calculation state needs evidence');
    }
    try {
      const computed = computeCoverage({ sourceId: o.sourceId, sourceVersion: o.sourceVersion, modality: o.modality, ...o.coverage, observations: [o] });
      if ((o.coverage.completeClaim || o.coverage.state === 'complete_for_declared_scope') && !computed.completeForDeclaredScope)
        add(p + '/coverage', 'false_complete_coverage', 'Ranges do not cover the declared request');
      if (o.coverage.completeClaim && o.coverage.scopeMode === 'whole_source' && !computed.fullSourceCovered)
        add(p + '/coverage', 'false_full_source_coverage', 'Full source total/representation not established');
    } catch (failure) { errors.push(...(failure.errors || [error(p, 'coverage_invalid', failure.message)])); }
    if (o.cacheComponents !== null) {
      try {
        if (cacheKey(o.cacheComponents) !== o.cacheKey) add(p, 'cache_key_mismatch', 'Cache key differs from its components');
        const c = o.cacheComponents;
        if (c.sourceId !== s.id || c.sourceContentDigest !== s.contentDigest || c.sourceVersion !== s.version || c.sourceIdentityBasis !== s.identityBasis ||
            c.processorId !== o.processor.id || c.processorVersion !== o.processor.version ||
            canonicalJSON(c.processingParameters) !== canonicalJSON(o.processor.parameters) || c.materialRole !== o.materialRole)
          add(p, 'cache_component_mismatch', 'Cache components do not describe this observation');
        const observedScope = {
          unit: o.coverage.unit,
          representation: o.coverage.representation,
          timebase: o.coverage.timebase,
          ranges: coverageUnion(o.coverage.observedRanges),
          anchors: [...new Set(o.anchors.map(a => canonicalJSON(a)))].sort()
        };
        const cacheRanges = coverageUnion(c.anchorRange.ranges);
        if (c.anchorRange.unit !== 'seconds' && cacheRanges.some(range => range.some(n => !Number.isInteger(n))) ||
            canonicalJSON({ ...c.anchorRange, ranges: cacheRanges, anchors: [...new Set(c.anchorRange.anchors)].sort() }) !== canonicalJSON(observedScope))
          add(p, 'cache_scope_mismatch', 'Cache range and anchor scope must match this observation');
      } catch (failure) { errors.push(...failure.errors); }
    } else if (o.cacheKey !== null) add(p, 'cache_without_components', 'Cache key needs all components');
  }
  checkCycle(observations, 'derivedFromObservationIds', '$/observations', errors);
  const unusableObservationIds = new Set([...observations.values()]
    .filter(o => ['invalidated', 'failed', 'not_observed', 'unsupported'].includes(o.status)).map(o => o.id));
  let propagated = true;
  while (propagated) {
    propagated = false;
    for (const o of observations.values()) {
      if (!unusableObservationIds.has(o.id) && o.derivedFromObservationIds.some(id => unusableObservationIds.has(id))) {
        unusableObservationIds.add(o.id); propagated = true;
        if (['observed', 'ambiguous', 'conflicted'].includes(o.status))
          add('$/observations/' + o.id, 'derived_from_unusable_observation', 'A current observation cannot descend from invalidated or unusable evidence');
      }
    }
  }
  const direct = ['source_fact', 'company_claim', 'independent_observation', 'user_statement'];
  for (const c of claims.values()) {
    const p = '$/claims/' + c.id;
    refs(c.sourceIds, sources, p + '/sourceIds'); refs(c.observationIds, observations, p + '/observationIds');
    refs(c.basisClaimIds, claims, p + '/basisClaimIds'); refs(c.conflictsWith, claims, p + '/conflictsWith');
    if (c.conflictsWith.includes(c.id)) add(p, 'self_conflict', 'A claim cannot conflict with itself');
    if (direct.includes(c.status) && (!c.sourceIds.length || !c.anchors.length)) add(p, 'claim_evidence_required', 'Direct claim needs source IDs and anchors');
    if (direct.includes(c.status) && c.sourceIds.some(id => !c.anchors.some(a => a.sourceId === id)))
      add(p, 'source_anchor_missing', 'Every direct evidence source needs a corresponding anchor');
    if (c.status === 'inference' && !c.basisClaimIds.length) add(p, 'inference_basis_missing', 'Inference needs explicit premise claims');
    if (c.status === 'unknown' && c.metric !== null && c.metric.value !== null) add(p, 'unknown_metric_value', 'Unknown metric value must remain null');
    if (c.status === 'hypothesis' && c.statementType === 'historical_result') add(p, 'hypothesis_as_result', 'Hypothesis cannot be a realized result');
    for (const id of c.sourceIds) {
      const s = sources.get(id); if (!s) continue;
      if (['reference_style', 'reference_layout', 'background_context', 'research_lead'].includes(s.materialRole))
        add(p, 'reference_role_as_evidence', 'Style/layout/context/leads cannot support business claims');
      if (direct.includes(c.status) && s.readStatus !== 'read') add(p, 'unread_source_as_evidence', 'Direct claim needs a read source; its actual readScope remains explicit');
      if (s.materialRole === 'synthetic_example' && c.evidenceContext !== 'synthetic') add(p, 'synthetic_claim_upgrade', 'Synthetic evidence must remain synthetic');
    }
    for (const a of c.anchors) {
      if (!c.sourceIds.includes(a.sourceId)) add(p + '/anchors', 'anchor_source_mismatch', 'Anchor must refer to a claim source');
      if (a.observationId !== null && (!c.observationIds.includes(a.observationId) || observations.get(a.observationId)?.sourceId !== a.sourceId))
        add(p + '/anchors', 'anchor_observation_mismatch', 'Anchor must match referenced observation/source');
    }
    for (const id of c.observationIds) {
      const o = observations.get(id); if (!o) continue;
      if (!c.sourceIds.includes(o.sourceId)) add(p, 'claim_observation_source_mismatch', 'Observed source missing from claim');
      if (direct.includes(c.status) && ['invalidated', 'failed', 'not_observed', 'unsupported'].includes(o.status))
        add(p, 'invalid_observation_as_evidence', 'Direct claim needs a current observed input');
      if (direct.includes(c.status)) {
        const observedTemporal = o.semantics.temporalMode;
        if (['historical_result', 'current_state'].includes(c.statementType) &&
            ['plan', 'target', 'budget', 'forecast', 'hypothesis'].includes(observedTemporal))
          add(p, 'claim_temporal_conflict', 'A plan, target, forecast, or hypothesis cannot directly support an actual-result/current-state claim');
        const observedPolarity = o.semantics.polarity;
        if (['affirmative', 'negative'].includes(c.polarity) && ['affirmative', 'negative'].includes(observedPolarity) && c.polarity !== observedPolarity)
          add(p, 'claim_polarity_conflict', 'A directly cited observation has the opposite polarity');
        if (['unknown', 'mixed'].includes(observedTemporal) || ['unknown', 'mixed'].includes(observedPolarity) ||
            c.statementType === 'unknown' || c.polarity === 'unknown')
          warn(p, 'semantic_alignment_review_required', 'Direct evidence has uncertain time/polarity semantics; keep the claim open for review');
      }
    }
    if (c.status === 'independent_observation' && !c.sourceIds.some(id => sources.get(id)?.independence === 'independent' && nonempty(sources.get(id)?.observationMethod)))
      add(p, 'independent_method_missing', 'Independent source and stated observation method required');
    if (c.status === 'user_statement' && !c.sourceIds.some(id => sources.get(id)?.materialRole === 'user_statement' || sources.get(id)?.independence === 'user'))
      add(p, 'user_statement_source_missing', 'User statement needs corresponding user source');
    if (c.evidenceContext === 'real' && c.basisClaimIds.some(id => claims.get(id)?.evidenceContext === 'synthetic'))
      add(p, 'synthetic_inference_upgrade', 'Synthetic premises cannot become real evidence');
  }
  checkCycle(claims, 'basisClaimIds', '$/claims', errors);
  for (const item of cases.values()) {
    const p = '$/cases/' + item.id;
    refs(item.claimIds, claims, p + '/claimIds'); refs(item.sourceIds, sources, p + '/sourceIds');
    if (direct.includes(item.evidenceStatus) && !item.claimIds.some(id => claims.get(id)?.status === item.evidenceStatus))
      add(p, 'case_evidence_upgrade', 'Case status needs a claim of that evidence nature');
    for (const id of item.claimIds) {
      const c = claims.get(id); if (!c) continue;
      if (c.sourceIds.some(id => !item.sourceIds.includes(id))) add(p, 'case_source_missing', 'Case must carry its claim sources');
      if (c.evidenceContext === 'synthetic' && item.evidenceContext !== 'synthetic') add(p, 'synthetic_case_upgrade', 'Synthetic claim cannot become a real case');
    }
    for (const [key, d] of Object.entries(item.innovationDimensions)) {
      refs(d.claimIds, claims, p + '/innovationDimensions/' + key);
      if (['supported', 'inference'].includes(d.status) && (!d.claimIds.length || !nonempty(d.summary)))
        add(p, 'dimension_evidence_missing', 'Supported dimension needs a summary and claim references');
      if (d.claimIds.some(id => !item.claimIds.includes(id))) add(p, 'dimension_case_mismatch', 'Dimension claim must belong to this case');
    }
  }
  for (const [key, values] of Object.entries(bundle.analysis)) for (const item of values) {
    refs(item.claimIds, claims, '$/analysis/' + key); refs(item.caseIds, cases, '$/analysis/' + key);
    if (item.kind === 'inference' && !item.claimIds.length) add('$/analysis/' + key, 'analysis_basis_missing', 'Analytical inference needs premises');
  }
  for (const o of bundle.outputs) {
    const p = '$/outputs/' + o.id;
    refs(o.sourceIds, sources, p); refs(o.claimIds, claims, p); refs(o.caseIds, cases, p);
    const stages = ['created', 'read_back', 'presented', 'accepted'], level = stages.indexOf(o.status);
    if (level >= 0) {
      if (!nonempty(o.pathOrChat)) add(p, 'output_location_missing', 'Realized output needs its actual location/chat ID');
      if (!o.deliveryMode) add(p, 'output_delivery_mode_missing', 'Realized output must declare chat or file delivery');
      if (o.deliveryMode === 'chat' && ['created', 'read_back'].includes(o.status))
        add(p, 'chat_output_file_stage_invalid', 'Chat delivery cannot claim file creation/read-back stages');
      const requiredStages = o.deliveryMode === 'chat' ? ['presented', ...(o.status === 'accepted' ? ['accepted'] : [])] : stages.slice(0, level + 1);
      for (const stage of requiredStages) if (!o.events.some(e => e.stage === stage))
        add(p, 'output_stage_evidence_missing', 'Missing event: ' + stage);
      if (o.checks.some(c => c.status === 'fail')) add(p, 'failed_output_promoted', 'Failed output check cannot yield successful stage');
      const realizedEvents = o.events.filter(e => ['created', 'read_back', 'presented'].includes(e.stage));
      for (const event of realizedEvents) {
        if (event.actorType !== 'tool' || !event.receipt)
          add(p, 'output_receipt_unverified', 'Create/read-back/presentation needs a structured tool receipt; model-only declarations are insufficient');
        else {
          if (event.evidenceRef !== event.receipt.operationId && event.receipt.operationId !== null)
            add(p, 'output_receipt_reference_mismatch', 'Event reference and receipt operation ID differ');
          if (Date.parse(event.receipt.observedAt) !== Date.parse(event.at))
            add(p, 'output_receipt_time_mismatch', 'Receipt time and event time differ');
        }
      }
      if (o.deliveryMode === 'file') {
        const expected = stages.slice(0, level + 1).filter(stage => stage !== 'accepted');
        const events = expected.map(stage => o.events.find(e => e.stage === stage)).filter(Boolean);
        if (events.length === expected.length) {
          const first = events[0].receipt;
          if (first) for (const event of events) if (event.receipt &&
            (event.receipt.artifactId !== first.artifactId || event.receipt.contentSha256 !== first.contentSha256 ||
             event.receipt.hostSurface !== first.hostSurface || event.receipt.sessionId !== first.sessionId))
            add(p, 'output_receipt_binding_mismatch', 'Create/read-back/present must bind the same artifact bytes and host session');
          for (let i = 1; i < events.length; i++) if (Date.parse(events[i].at) < Date.parse(events[i - 1].at))
            add(p, 'output_event_order_invalid', 'Output stages must occur in chronological order');
        }
      }
    }
    if (o.status === 'accepted' && !o.events.some(e => e.stage === 'accepted' && ['user', 'external'].includes(e.actorType)))
      add(p, 'model_acceptance_upgrade', 'Model review is not user acceptance');
    if (o.status === 'planned' && o.events.length) add(p, 'planned_output_has_events', 'Planned output cannot inherit completed events');
  }
  if (bundle.continuation !== null) {
    for (const source of bundle.continuation.sources) {
      const current = sources.get(source.id);
      if (!current) add('$/continuation/sources', 'dangling_reference', 'Unknown continuation source: ' + source.id);
      else if (source.contentDigest !== current.contentDigest || source.version !== current.version ||
          (source.derivedFrom ?? null) !== (current.derivedFrom ?? null))
        add('$/continuation/sources', 'continuation_source_drift', 'Continuation snapshot must be reconciled to current source identity');
    }
    for (const state of bundle.continuation.observationStates) {
      const observation = observations.get(state.id);
      if (!observation || observation.sourceId !== state.sourceId)
        add('$/continuation/observationStates', 'dangling_reference', 'Continuation observation/source does not match current records');
      else if (observation.status !== state.status || observation.cacheKey !== state.cacheKey ||
          canonicalJSON(observation.cacheComponents) !== canonicalJSON(state.cacheComponents) ||
          canonicalJSON(observation.derivedFromObservationIds) !== canonicalJSON(state.derivedFromObservationIds || []))
        add('$/continuation/observationStates/' + state.id, 'continuation_state_mismatch', 'Continuation is a state projection and must match the current observation record');
    }
    try {
      const checked = reconcileContinuation(bundle.continuation, {});
      if (checked.newlyInvalidatedObservationIds.length) add('$/continuation', 'continuation_requires_reconciliation', 'Stale processing records require reconciliation');
    } catch (failure) { errors.push(...(failure.errors || [error('$/continuation', 'continuation_invalid', failure.message)])); }
  }
  const outputEventsExist = bundle.outputs.some(o => o.status !== 'planned');
  return { valid: errors.length === 0, errors: errors.slice(0, 200), warnings: warnings.slice(0, 200),
    hostEvidenceStatus: outputEventsExist ? 'claimed_unverified' : 'not_run',
    semanticTruthStatus: 'not_certified_by_schema_validation' };
}
export function planResearch(brief) {
  requireValid(brief, 'common.schema.json', 'brief');
  if (!nonempty(brief.question)) reject('brief_question_missing', 'Provide the actual research question before planning');
  if (brief.sourcePolicy.mode === 'only' && !brief.sourcePolicy.domains.length) reject('source_scope_empty', 'An only-source policy needs explicit domains');
  for (const d of brief.sourcePolicy.domains) if (!/^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/i.test(d))
    reject('source_domain_invalid', 'Source domains must be hostnames, not queries or URLs');
  const t = brief.searchTerms;
  const groups = [['direct', [...t.industry, ...t.workflow]],
    ['mechanism', t.mechanism.length ? t.mechanism : t.workflow],
    ['conditions', [...t.conditions, ...t.workflow]]];
  const methods = {
    case_comparison: ['define_comparable_cases', 'read_original_sources', 'deduplicate_source_families', 'compare_conditions'],
    case_analysis: ['decision_context', 'before_after_workflow', 'evidence_and_countercase'],
    tool_comparison: ['constraint_screening', 'current_product_evidence', 'full_cost_and_trial'],
    action_method: ['baseline_and_responsibility', 'reusable_steps', 'acceptance_and_stop_conditions'],
    communication: ['audience_first_synthesis', 'source_preserving_delivery', 'revision_scope']
  };
  const families = [...new Set([brief.primaryDeliverable, ...brief.additionalDeliverables])];
  const matrix = brief.researchMode === 'materials_only' ? [] : groups.map(([relation, items]) => {
    const terms = [...new Set(items.filter(nonempty))];
    const query = (terms.length ? [brief.geography.join(' '), ...terms, brief.timeRange || '', '案例 实施 结果'] :
      [brief.question, brief.geography.join(' '), brief.timeRange || '']).filter(nonempty).join(' ');
    const scopedQuery = brief.sourcePolicy.mode === 'only' ? query + ' (' + brief.sourcePolicy.domains.map(d => 'site:' + d).join(' OR ') + ')' : query;
    return { relation, query: scopedQuery, domains: [...brief.sourcePolicy.domains],
      domainQueries: brief.sourcePolicy.domains.map(d => query + ' site:' + d),
      sourcePolicy: brief.sourcePolicy.mode, requiredGeography: [...brief.geography],
      screeningCriteria: [...brief.constraints], executionState: 'not_executed' };
  });
  return { briefId: brief.id, question: brief.question, queryMatrix: matrix,
    researchMode: brief.researchMode, methods: [...new Set(families.flatMap(f => methods[f]))],
    deliverables: families.map((family, i) => ({ family, priority: i ? 'additional' : 'primary', formats: [...brief.formats], status: 'planned' })),
    requestedCount: brief.requestedCount, constraints: [...brief.constraints], unknowns: [...brief.unknowns],
    performedSearch: false, inferredUserFacts: [] };
}
const htmlEscape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
const mdEscape = value => String(value).replaceAll('\\', '\\\\').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replace(/([[\]()*_\u0060|])/g, '\\$1').replaceAll('\r', '').replaceAll('\n', ' / ');
const display = value => value === null || value === undefined ? '未知' : typeof value === 'object' ? canonicalJSON(value) : String(value);
const csvQuote = value => '"' + String(value).replaceAll('"', '""') + '"';
const evidenceText = { source_fact: '已读来源直接支持', company_claim: '企业或供应商自述',
  independent_observation: '独立机构观察', user_statement: '用户陈述',
  inference: '研究推断', hypothesis: '待验证假设', unknown: '未知' };
const timeText = { historical_result: '历史结果', future_plan: '未来计划', current_state: '当前状态', unknown: '未知' };
const contextText = { real: '真实资料范围', synthetic: '合成示例' };
function readableMetric(metric) {
  if (!metric) return '未提供指标；不据此推导收益';
  const labels = { name:'指标', value:'数值', unit:'单位', denominator:'分母', baseline:'基线', comparisonPeriod:'对照时期', method:'方法', currency:'币种' };
  return Object.entries(labels).map(([key,label])=>label+'：'+display(metric[key])).join('；');
}
function readableConditions(value) {
  const labels={industryPosition:'产业位置',existingSystems:'既有系统',knowledgeResources:'知识资源',resourceConstraints:'资源约束',dataRights:'数据权利',decisionOwner:'决策责任',marketRegion:'市场地区'};
  const known=[],unknown=[];
  for(const [key,item] of Object.entries(value||{})) (item===null?unknown:known).push(item===null?(labels[key]||key):(labels[key]||key)+'：'+display(item));
  return [...known,...(unknown.length?['待确认：'+unknown.join('、')]:[])].join('；') || '尚未记录适用条件';
}
function safeLink(uri) {
  try { const url = new URL(uri); return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : null; }
  catch { return null; }
}
function sourceLink(source) {
  // The observed final address takes precedence over a title or original URL.
  // A requested-only address is not silently presented as the address actually read.
  return safeLink(source.effectiveUrl) || safeLink(source.uriOrLabel);
}
export function validateClaims(brief, claims) {
  const value = { schemaVersion: 'research.claims-lite/v1', brief, claims };
  const structural = validateSchema(value, 'claims-lite.schema.json');
  if (!structural.valid) return { ...structural, warnings: [], evidenceStatus: 'structure_invalid',
    sourceAuthenticityVerified: false, semanticTruthCertified: false, networkCalled: false, bundleMigrationPerformed: false };
  return checkClaimsRelations(brief, claims);
}
export function assessDelivery(brief, claims, delivery) {
  const validation = validateClaims(brief, claims);
  assertJSON(delivery);
  if (!Array.isArray(claims) || !claims.every(plain)) return { readyForDelivery: false,
    status: 'claim_records_invalid', validation, gates: [], unmetItems: [], hostExecutionProven: false };
  return { ...assessDeliveryRecords(validation, claims, delivery), validation };
}
export function renderResearch(bundle) {
  const result = validateResearch(bundle);
  if (!result.valid) throw new KernelInputError(result.errors);
  const claims = new Map(bundle.claims.map(c => [c.id, c]));
  const sources = new Map(bundle.sources.map(s => [s.id, s])), rows = [];
  const assigned = new Set(bundle.cases.flatMap(c => c.claimIds));
  const unassigned = bundle.claims.filter(c => !assigned.has(c.id));
  const renderItems = [...bundle.cases];
  if (unassigned.length) renderItems.push({
    id: '[unassigned]', organization: '未归案主张', innovation: '研究记录',
    evidenceStatus: 'unknown', evidenceContext: unassigned.some(c => c.evidenceContext === 'synthetic') ? 'synthetic' : 'real',
    problem: null, before: null, change: null, aiRole: null, humanRole: null, outputs: [], acceptanceAndFeedback: [],
    claimIds: unassigned.map(c => c.id), sourceIds: [...new Set(unassigned.flatMap(c => c.sourceIds))],
    innovationDimensions: {}, chinaContext: {}, unknowns: ['尚未归入具体案例，不计入合格案例数量']
  });
  for (const item of renderItems) for (const id of item.claimIds.length ? item.claimIds : [null]) {
    const c = claims.get(id);
    rows.push([item.id, item.organization, item.innovation, c?.id || '', c?.status || item.evidenceStatus,
      c?.evidenceContext || item.evidenceContext, c?.statementType || 'unknown', c?.polarity || 'unknown',
      c?.text || '当前没有可归入该案的主张', display(c?.period ?? item.period),
      (c?.sourceIds || item.sourceIds).join(';'), canonicalJSON(c?.anchors || []),
      canonicalJSON(c?.qualifiers || []), canonicalJSON(c?.conditions || []),
      canonicalJSON(c?.metric ?? null), canonicalJSON(c?.limitations || item.unknowns),
      canonicalJSON((c?.observationIds || []).map(id => bundle.observations.find(o => o.id === id)))]);
  }
  const headers = ['case_id', 'organization', 'innovation', 'claim_id', 'evidence_status',
    'evidence_context', 'statement_type', 'polarity', 'claim_text', 'period', 'source_ids',
    'anchors_json', 'qualifiers_json', 'conditions_json', 'metric_json', 'limitations_json', 'observations_json'];
  // CSV formula neutralization is reversible: any changed cell retains its
  // original value in escaped_fields_json. RFC4180 quoting alone is not enough.
  const csvRows = rows.map(row => {
    const escaped = {};
    const safe = row.map((v, i) => {
      const text = display(v);
      if (/^[\s]*[=+\-@]|^[\t\r]/.test(text)) { escaped[headers[i]] = text; return "'" + text; }
      return text;
    });
    return [...safe, canonicalJSON(escaped)];
  });
  const csv = [headers.concat(['escaped_fields_json']), ...csvRows].map(r => r.map(csvQuote).join(',')).join('\r\n') + '\r\n';
  const md = ['# ' + mdEscape(bundle.researchBrief.question), '',
    '读者：' + mdEscape(display(bundle.researchBrief.audience)),
    '研究模式：' + ({live_search:'当前资料检索',materials_only:'仅使用所给材料'}[bundle.researchBrief.researchMode] || bundle.researchBrief.researchMode) + '；要求数量：' + display(bundle.researchBrief.requestedCount),
    '约束：' + bundle.researchBrief.constraints.map(mdEscape).join('；'), '',
    '本成品由给定研究记录确定性生成；不表示新执行了搜索、媒体感知或事实审计。', ''];
  if (result.warnings.length) {
    md.push('## 需要复核的研究语义', '');
    for (const warning of result.warnings) md.push('- ' + mdEscape(warning.path + '：' + warning.message));
    md.push('');
  }
  const directStatuses = new Set(['source_fact', 'company_claim', 'independent_observation', 'user_statement']);
  const directlyCitedCases = bundle.cases.filter(item => item.evidenceContext === 'real' &&
    item.claimIds.some(id => directStatuses.has(claims.get(id)?.status)));
  const citedFamilyIds = new Set(directlyCitedCases.flatMap(item => item.sourceIds.map(id => sources.get(id)?.sourceFamily).filter(Boolean)));
  const deliverableHeading = {
    case_comparison: '案例比较结论', case_analysis: '单案分析结论',
    tool_comparison: '工具比较结论', action_method: '借鉴路径与试点', communication: '沟通简报'
  }[bundle.researchBrief.primaryDeliverable];
  md.push('## ' + deliverableHeading, '');
  for (const item of bundle.analysis.recommendations) {
    md.push('- ' + mdEscape(item.text) + ' [' + (evidenceText[item.kind] || item.kind) + ']');
    const basis = item.claimIds.map(id => claims.get(id)).filter(Boolean);
    const conditions = [...new Set(basis.flatMap(claim => claim.conditions))];
    const limits = [...new Set(basis.flatMap(claim => claim.limitations))];
    md.push('  - 依据：' + (item.claimIds.map(mdEscape).join('、') || '未关联主张；适用性待核实'));
    if (conditions.length) md.push('  - 依据中的成立条件：' + mdEscape(conditions.join('；')));
    if (limits.length) md.push('  - 依据中的限制：' + mdEscape(limits.join('；')));
  }
  if (!bundle.analysis.recommendations.length) md.push('当前没有可交付的结论建议；以下记录用于展示已核验内容和证据缺口。');
  md.push('', '## 案例与证据覆盖', '',
    '案例记录：' + bundle.cases.length + '；有直接来源主张的真实案例记录：' + directlyCitedCases.length +
    '；涉及来源家族：' + citedFamilyIds.size + '。来源家族数不等于独立案例数或因果证据。');
  if (bundle.researchBrief.requestedCount !== null && directlyCitedCases.length < bundle.researchBrief.requestedCount)
    md.push('距用户要求数量还缺' + (bundle.researchBrief.requestedCount - directlyCitedCases.length) + '条有直接来源主张的真实案例记录；不能用转载、合成或推测补齐。');
  md.push('案例无法完成或条件不明的部分保留为缺口，不转换成已验证成果。', '');
  for (const item of renderItems) {
    md.push('## ' + mdEscape(item.organization) + '：' + mdEscape(item.innovation), '',
      '证据：' + evidenceText[item.evidenceStatus] + '；情境：' + (contextText[item.evidenceContext] || item.evidenceContext),
      '问题：' + mdEscape(display(item.problem)), '原流程：' + mdEscape(display(item.before)),
      '变化：' + mdEscape(display(item.change)), 'AI职责：' + mdEscape(display(item.aiRole)),
      '人工职责：' + mdEscape(display(item.humanRole)), '交付物：' + item.outputs.map(mdEscape).join('；'),
      '验收与反馈：' + mdEscape(item.acceptanceAndFeedback.length ? item.acceptanceAndFeedback.join('；') : '尚未提供'), '');
    for (const id of item.claimIds) {
      const c = claims.get(id);
      md.push('- [' + c.id + '] ' + mdEscape(c.text),
        '  - 性质：' + evidenceText[c.status] + '；时间语义：' + (timeText[c.statementType] || c.statementType) + '；表述：' + ({affirmative:'肯定',negative:'否定',unknown:'未知'}[c.polarity] || c.polarity) + '；时期：' + mdEscape(display(c.period)),
        '  - 限定：' + mdEscape(c.qualifiers.join('；') || '无附加限定记录') + '；条件：' + mdEscape(c.conditions.join('；') || '未给'),
        '  - 指标口径：' + mdEscape(readableMetric(c.metric)),
        '  - 依据：' + c.anchors.map(a => mdEscape(a.sourceId + ' ' + a.locator + (a.exactQuote === null ? '' : ' 原文：' + a.exactQuote))).join('；'),
        '  - 限制/冲突：' + mdEscape([...c.limitations, ...c.conflictsWith.map(id => '与' + id + '冲突')].join('；') || '未提供'));
      for (const observationId of c.observationIds) {
        const o = bundle.observations.find(o => o.id === observationId);
        const unit = {paragraphs:'段落',pages:'页',seconds:'秒',frames:'帧',rows:'行',cells:'单元格'}[o.coverage.unit] || o.coverage.unit;
        const ranges = o.coverage.observedRanges.map(([start,end])=>'['+start+','+end+')').join('、') || '未观察';
        md.push('  - 观察范围：' + mdEscape(o.id + '；'+unit+'区间 '+ranges+'（0基半开）；已知总量：'+display(o.coverage.knownTotal)+
          '；方式：'+({text_extraction:'文本读取',synthetic_observation_fixture:'合成观察夹具',ocr:'OCR'}[o.observationKind] || o.observationKind)));
        if ((o.limitations||[]).length) md.push('  - 观察限制：'+mdEscape(o.limitations.join('；')));
        if (o.tabularContext) md.push('  - 表格读取：保留原表上下文，详见逐项审计附录；不能只凭一个单元格推断完整口径。');
      }
    }
    for (const [key, value] of Object.entries(item.innovationDimensions))
      md.push('- ' + DIMENSIONS[key] + '：' + value.status + '；' + mdEscape(display(value.summary)) + '；依据：' + value.claimIds.join(','));
    md.push('中国企业条件：' + mdEscape(readableConditions(item.chinaContext)), '未知：' + item.unknowns.map(mdEscape).join('；'), '');
  }
  const analysisTitles = { similarities: '可迁移的共同机制', mechanisms: '变化机制', alternativeExplanations: '竞争解释', failureConditions: '失效条件', commonalities: '可迁移的共同机制', differences: '差异与边界', recommendations: '建议与行动',
    competingExplanations: '竞争解释', transferConditions: '迁移条件', conflicts: '冲突与未决项', openQuestions: '开放问题' };
  for (const [name, items] of Object.entries(bundle.analysis)) if (items.length) {
    md.push('## ' + (analysisTitles[name] || name), '');
    for (const item of items) md.push('- ' + mdEscape(item.text) + ' [' + (evidenceText[item.kind] || item.kind) + '；主张 ' + item.claimIds.join(',') + ']');
    md.push('');
  }
  md.push('## 来源与读取范围', '');
  for (const s of bundle.sources) md.push('- ' + s.id + '：' + mdEscape(s.uriOrLabel) + '；主体：' + mdEscape(display(s.publisher)) +
    '；来源地址：' + (sourceLink(s) ? mdEscape(sourceLink(s)) : '未记录可打开的网页地址；按材料名称和锚点核对') +
    '；发布：' + display(s.publishedAt || s.publishedDate) + (s.publishedDate && !s.publishedAt ? '（仅日期，时刻未知）' : '') + '；事件：' + display(s.eventAt) + '；读取：' + display(s.readAt) +
    '；' + ({read:'已读',partially_read:'部分读取',metadata_only:'仅元数据',not_read:'未读'}[s.readStatus] || s.readStatus) + ' / ' + mdEscape(s.readScope) + '；角色：' + ({fact_evidence:'事实材料',synthetic_example:'合成示例',method_reference:'方法参考'}[s.materialRole] || s.materialRole) + '；家族：' + s.sourceFamily +
    '；限制：' + s.limitations.map(mdEscape).join('；'));
  const table = '<table id="claims" class="audit-table"><thead><tr>' + headers.map(h => '<th scope="col">' + h + '</th>').join('') +
    '</tr></thead><tbody>' + rows.map(row => '<tr>' + row.map(cell => '<td>' + htmlEscape(display(cell)) + '</td>').join('') + '</tr>').join('') + '</tbody></table>';
  const links = bundle.sources.map(s => '<li>' + htmlEscape(s.id) + ' ' + (sourceLink(s) ?
    '<a rel="noopener noreferrer" href="' + htmlEscape(sourceLink(s)) + '">' + htmlEscape(s.uriOrLabel) + '</a>' : htmlEscape(s.uriOrLabel) + '（未记录可打开的网页地址）') +
    '；读取范围：' + htmlEscape(s.readScope) + '</li>').join('');
  const embedded = canonicalJSON(bundle).replaceAll('<', '\\u003c').replaceAll('>', '\\u003e').replaceAll('&', '\\u0026');
  const presentation = renderSemanticMarkdown(md.join('\n'));
  const html = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<title>' + htmlEscape(bundle.researchBrief.question) + '</title><style>' + RESEARCH_CSS + '</style></head><body><div class="page">' +
    '<header><p class="brand">高创智库 · 智能原生案例研究员</p><p class="scope-note">研究判断以所列来源、实际读取范围和限制为准；来源披露不等于独立核验或本企业收益。</p></header>' +
    '<div class="report-layout">' + presentation.navigation + '<main id="narrative">' + presentation.body + '</main></div>' +
    '<section class="appendix" aria-label="可打开的来源"><h2>可打开的来源</h2><ul class="source-index">' + links + '</ul></section>' +
    '<details class="appendix"><summary>逐项审计附录：主张、范围与完整记录</summary><p>此表保留可核对字段；主结论和限定已在正文呈现。</p><div class="table-scroll" role="region" aria-label="完整主张审计表" tabindex="0">' + table + '</div></details>' +
    '<p class="footer">产品版本2026.11.3。文件生成、宿主呈现、用户接受和企业采用分别验收。</p></div><script id="research-data" type="application/json">' + embedded + '</script></body></html>';
  return { markdown: md.join('\n') + '\n', csv, html,
    summary: { totalCaseCount: bundle.cases.length, directlyCitedCaseCount: directlyCitedCases.length,
      citedSourceFamilyCount: citedFamilyIds.size, evidenceSufficiency: 'not_certified_by_renderer',
      clickableSourceCount: bundle.sources.filter(source => sourceLink(source)).length,
      sourcesWithoutClickableUrl: bundle.sources.filter(source => !sourceLink(source)).map(source => source.id),
      semanticHtmlGenerated: true, visualInspectionPerformed: false, userAcceptanceProven: false } };
}
export function renderLegacyResearch(bundle) {
  assertJSON(bundle);
  if (!plain(bundle) || bundle.schemaVersion !== 'research.bundle/v1' || !plain(bundle.researchBrief) ||
      !Array.isArray(bundle.sources) || !Array.isArray(bundle.claims) || !Array.isArray(bundle.cases))
    reject('legacy_bundle_invalid', 'Read-only archive viewer accepts only structurally recognizable version 1 research bundles');
  const md = [
    '# ' + mdEscape(display(bundle.researchBrief.question)), '',
    '归档查看模式：这是旧版本研究记录，原始文字只读保留。缓存范围、派生关系和交付回执未按2026.9.23规则重新核验；本展示不将原主张确认为当前有效证据。', '',
    '读者：' + mdEscape(display(bundle.researchBrief.audience)),
    '旧版记录案例：' + bundle.cases.length + '；来源记录：' + bundle.sources.length, ''
  ];
  for (const item of bundle.cases) {
    md.push('## ' + mdEscape(display(item.organization)) + '：' + mdEscape(display(item.innovation)), '',
      '历史记录标注：' + mdEscape(display(item.evidenceStatus)) + '；案例情境：' + mdEscape(display(item.evidenceContext)),
      '问题：' + mdEscape(display(item.problem)), '变化：' + mdEscape(display(item.change)),
      '人工职责：' + mdEscape(display(item.humanRole)),
      '验收与反馈：' + mdEscape((item.acceptanceAndFeedback || []).map(display).join('；') || '旧记录未提供'),
      '归档未知项：' + mdEscape((item.unknowns || []).map(display).join('；') || '旧记录未提供'), '');
    for (const id of item.claimIds || []) {
      const claim = bundle.claims.find(c => c.id === id);
      if (claim) md.push('- [归档主张 ' + mdEscape(claim.id) + '；未经当前规则复核] ' + mdEscape(claim.text));
    }
    md.push('');
  }
  const assigned = new Set(bundle.cases.flatMap(item => item.claimIds || []));
  const unassigned = bundle.claims.filter(claim => !assigned.has(claim.id));
  if (unassigned.length) {
    md.push('## 未归入案例的旧版主张（未重新核验）', '');
    for (const claim of unassigned) md.push('- [' + mdEscape(claim.id) + '] ' + mdEscape(claim.text));
    md.push('');
  }
  if (plain(bundle.analysis)) for (const [section, items] of Object.entries(bundle.analysis)) if (Array.isArray(items) && items.length) {
    md.push('## 旧版分析：' + mdEscape(section), '');
    for (const item of items) md.push('- ' + mdEscape(item.text));
    md.push('');
  }
  if (Array.isArray(bundle.outputs) && bundle.outputs.length) {
    md.push('## 旧版交付记录（未经阶段回执复核）', '');
    for (const output of bundle.outputs) md.push('- ' + mdEscape(output.id) + '；' + mdEscape(output.format) +
      '；旧状态=' + mdEscape(output.status) + '；位置=' + mdEscape(display(output.pathOrChat)));
    md.push('');
  }
  md.push('## 来源索引', '');
  for (const source of bundle.sources) md.push('- ' + mdEscape(source.id) + '：' + mdEscape(source.uriOrLabel) +
    '；旧版读取状态：' + mdEscape(display(source.readStatus)) + '；旧版范围：' + mdEscape(display(source.readScope)));
  return { markdown: md.join('\n') + '\n', compatibilityStatus: 'legacy_read_only_unverified', filesModified: false };
}
// changes is a data patch; it does not read, modify or delete user source files.
export function reconcileContinuation(previous, changes) {
  requireValid(previous, 'continuation.schema.json'); assertJSON(changes);
  const allowed = new Set(['version', 'currentQuestion', 'confirmedChoices', 'sources', 'removedSourceIds',
    'processingUpdates', 'sections', 'nextAction', 'completed', 'openItems', 'constraints', 'audience',
    'primaryDeliverable']);
  if (!plain(changes) || Object.keys(changes).some(k => !allowed.has(k))) reject('continuation_patch_invalid', 'Unknown change field');
  for (const key of ['sources', 'removedSourceIds', 'processingUpdates', 'sections', 'completed', 'openItems', 'constraints'])
    if (changes[key] !== undefined && !Array.isArray(changes[key])) reject('continuation_patch_invalid', key + ' must be an array');
  const record = clone(previous), errors = [], conflicts = [], reasons = new Map();
  const sources = indexById(record.sources, '$/sources', errors), processing = indexById(record.observationStates, '$/observationStates', errors);
  indexById(record.reviews, '$/reviews', errors); indexById(record.sections, '$/sections', errors);
  if (errors.length) throw new KernelInputError(errors);
  const newlyInvalidated = new Set();
  for (const o of record.observationStates) if (o.status === 'invalidated') reasons.set(o.id, [...o.invalidationReasons]);
  const changedSources = new Set();
  for (const next of changes.sources || []) {
    requireValid(next, 'common.schema.json', 'sourceFingerprint');
    if (!sources.has(next.id) || canonicalJSON(sources.get(next.id)) !== canonicalJSON(next)) changedSources.add(next.id);
    sources.set(next.id, clone(next));
  }
  for (const id of changes.removedSourceIds || []) {
    if (!sources.has(id)) reject('continuation_source_missing', 'Cannot remove unknown source');
    sources.set(id, { id, contentDigest: null, version: null, identityBasis: 'unknown' }); changedSources.add(id);
  }
  let sourceDescendantsChanged = true;
  while (sourceDescendantsChanged) {
    sourceDescendantsChanged = false;
    for (const source of sources.values()) if (source.derivedFrom && changedSources.has(source.derivedFrom) && !changedSources.has(source.id)) {
      changedSources.add(source.id); sourceDescendantsChanged = true;
    }
  }
  const updates = new Map();
  for (const update of changes.processingUpdates || []) {
    if (!plain(update) || Object.keys(update).some(k => !['observationId', 'cacheComponents'].includes(k)) ||
        !processing.has(update.observationId) || updates.has(update.observationId)) reject('processing_update_invalid', 'Unique existing observation ID required');
    requireValid(update.cacheComponents, 'common.schema.json', 'cacheComponents');
    if (update.cacheComponents.sourceId !== processing.get(update.observationId).sourceId) reject('processing_source_mismatch', 'Cannot reassign an observation source');
    updates.set(update.observationId, update.cacheComponents);
  }
  const reused = [];
  for (const o of record.observationStates) {
    const oldStatus = o.status;
    const source = sources.get(o.sourceId);
    if (!source) reject('continuation_source_missing', 'Observation source is unknown');
    const before = o.cacheComponents, replacement = updates.get(o.id);
    const components = replacement ? clone(replacement) : before ? clone(before) : null, why = [];
    if (changedSources.has(source.id)) why.push('source_identity_or_version_changed');
    if (replacement && canonicalJSON(replacement) !== canonicalJSON(before)) why.push('processing_parameters_scope_or_purpose_changed');
    if (components) {
      components.sourceContentDigest = source.contentDigest; components.sourceVersion = source.version;
      components.sourceIdentityBasis = source.identityBasis;
    }
    let nextKey = null;
    try { if (components) nextKey = cacheKey(components); } catch { why.push('source_or_processing_identity_unknown'); }
    if (!components && ['observed', 'ambiguous', 'conflicted'].includes(o.status)) why.push('cache_components_missing');
    if (nextKey !== o.cacheKey) why.push('cache_key_changed');
    if (why.length) {
      o.status = 'invalidated'; o.invalidationReasons = [...new Set([...o.invalidationReasons, ...why])]; reasons.set(o.id, o.invalidationReasons);
      if (oldStatus !== 'invalidated') newlyInvalidated.add(o.id);
    } else if (['observed', 'ambiguous', 'conflicted'].includes(o.status) && nextKey !== null) reused.push(o.id);
    o.cacheComponents = nextKey === null ? null : components; o.cacheKey = nextKey;
  }
  let observationDescendantsChanged = true;
  while (observationDescendantsChanged) {
    observationDescendantsChanged = false;
    for (const o of record.observationStates) {
      const parents = o.derivedFromObservationIds || [];
      for (const parentId of parents) if (!processing.has(parentId))
        reject('continuation_observation_parent_missing', 'Derived observation references an unknown processing state');
      if (o.status !== 'invalidated' && parents.some(id => ['failed', 'unknown', 'invalidated'].includes(processing.get(id).status))) {
        o.status = 'invalidated';
        o.invalidationReasons = [...new Set([...o.invalidationReasons, 'derived_from_unusable_ancestor'])];
        reasons.set(o.id, o.invalidationReasons); newlyInvalidated.add(o.id); observationDescendantsChanged = true;
      } else if (o.status === 'invalidated') reasons.set(o.id, [...o.invalidationReasons]);
    }
  }
  const contextFields = ['currentQuestion', 'confirmedChoices', 'constraints', 'audience', 'primaryDeliverable'];
  const contextChangedFields = contextFields.filter(key => Object.hasOwn(changes, key) &&
    canonicalJSON(changes[key]) !== canonicalJSON(Object.hasOwn(previous, key) ? previous[key] : null));
  const contextChanged = contextChangedFields.length > 0;
  for (const r of record.reviews) {
    if (r.observationIds.some(id => !processing.has(id))) reject('continuation_review_reference', 'Review observation is unknown');
    const unusable = r.observationIds.some(id => ['failed', 'unknown', 'invalidated'].includes(processing.get(id).status));
    if (contextChanged || r.observationIds.some(id => reasons.has(id)) || r.status === 'valid' && unusable) {
      r.status = 'invalidated'; r.reason = contextChanged ? 'research_context_changed:' + contextChangedFields.join(',') : unusable ? 'dependency_not_current' : 'observation_inputs_changed';
    }
  }
  const sections = new Map(record.sections.map(s => [s.id, s]));
  for (const s of changes.sections || []) {
    requireValid(s, 'common.schema.json', 'section');
    const old = sections.get(s.id);
    if (old && (old.author === 'user' || old.locked) && canonicalJSON(old) !== canonicalJSON(s))
      conflicts.push({ sectionId: s.id, reason: 'user_or_locked_content_preserved', proposedContent: s.content });
    else sections.set(s.id, clone(s));
  }
  for (const s of sections.values()) {
    if (s.sourceIds.some(id => !sources.has(id)) || s.observationIds.some(id => !processing.has(id)))
      reject('continuation_section_reference', 'Unknown section material or observation');
    if (contextChanged || s.sourceIds.some(id => changedSources.has(id)) || s.observationIds.some(id =>
      reasons.has(id) || ['failed', 'unknown', 'invalidated'].includes(processing.get(id).status))) s.needsReview = true;
  }
  record.sources = [...sources.values()]; record.sections = [...sections.values()];
  record.sourceChanges = [...new Set([...record.sourceChanges, ...changedSources])];
  record.invalidatedReviews = [...new Set([...record.invalidatedReviews, ...record.reviews.filter(r => r.status === 'invalidated').map(r => r.id)])];
  const progressBefore = { completed: [...record.completed], openItems: [...record.openItems] };
  for (const key of ['version', 'currentQuestion', 'confirmedChoices', 'constraints', 'audience', 'primaryDeliverable', 'completed', 'openItems', 'nextAction'])
    if (Object.hasOwn(changes, key)) record[key] = clone(changes[key]);
  requireValid(record, 'continuation.schema.json');
  return { record, changedSourceIds: [...changedSources], invalidatedObservationIds: [...reasons.keys()],
    newlyInvalidatedObservationIds: [...newlyInvalidated],
    invalidatedClaimIds: [...new Set(record.observationStates.filter(o => reasons.has(o.id)).flatMap(o => o.claimIds))],
    invalidatedReviewIds: record.reviews.filter(r => r.status === 'invalidated').map(r => r.id),
    reusedObservationIds: reused, conflicts, contextChanged, contextChangedFields,
    progressChanged: canonicalJSON(progressBefore) !== canonicalJSON({ completed: record.completed, openItems: record.openItems }),
    filesModified: false };
}
export function collectResults(expectedIds, results) {
  assertJSON(expectedIds); assertJSON(results);
  if (!Array.isArray(expectedIds) || !expectedIds.length || expectedIds.some(id => !nonempty(id)) ||
      new Set(expectedIds).size !== expectedIds.length || !Array.isArray(results))
    reject('result_collection_input_invalid', 'Expected IDs must be unique and nonempty, and results must be an array');
  const expected = new Set(expectedIds), groups = new Map(), invalidResults = [], unexpectedIds = [];
  for (const [index, result] of results.entries()) {
    if (!plain(result) || !nonempty(result.id)) { invalidResults.push({ index, reason: 'result_id_missing' }); continue; }
    if (!expected.has(result.id)) unexpectedIds.push(result.id);
    const group = groups.get(result.id) || []; group.push({ index, result }); groups.set(result.id, group);
  }
  const duplicateIds = [...groups].filter(([, group]) => group.length > 1).map(([id]) => id);
  const validResults = [], failedResults = [];
  for (const id of expectedIds) {
    const group = groups.get(id);
    if (!group || group.length !== 1) continue;
    const { index, result } = group[0];
    if (['failed', 'partial'].includes(result.status)) { failedResults.push(clone(result)); continue; }
    if (!['valid', 'success', 'succeeded'].includes(result.status)) { invalidResults.push({ index, id, reason: 'result_status_invalid' }); continue; }
    const hasPayload = Object.hasOwn(result, 'payload') && result.payload !== null &&
      (typeof result.payload === 'string' ? nonempty(result.payload) : Array.isArray(result.payload) ?
        result.payload.length > 0 : plain(result.payload) ? Object.keys(result.payload).length > 0 : true);
    if (!hasPayload && !sha(result.sourceHash)) { invalidResults.push({ index, id, reason: 'result_payload_missing' }); continue; }
    validResults.push(clone(result));
  }
  const missingIds = expectedIds.filter(id => !groups.has(id));
  const branchesComplete = validResults.length === expectedIds.length && !failedResults.length &&
    !missingIds.length && !duplicateIds.length && !unexpectedIds.length && !invalidResults.length;
  return { validResults, failedResults, missingIds, duplicateIds, unexpectedIds: [...new Set(unexpectedIds)],
    invalidResults, branchesComplete, complete: branchesComplete, evidenceSufficiency: 'not_assessed',
    uniqueSourceFamilies: null, qualifiedCaseCount: null,
    completionMeaning: 'complete is a backward-compatible alias for branchesComplete only; case independence and evidence sufficiency require separate research-level review' };
}

// BEGIN FINAL ANSWER BUDGET
/** Validate the exact complete message, including requested notes, without truncating. */
export function assessFinalAnswerBudget({ body, additions = [], maxCharacters, countReportRequested = false } = {}) {
  if (typeof body !== 'string' || !body.trim() || !Array.isArray(additions) ||
      additions.some(text => typeof text !== 'string') || !Number.isSafeInteger(maxCharacters) || maxCharacters < 1)
    return { status: 'invalid_final_answer_budget_input', readyForDelivery: false, outputText: null };
  const finalText = [body, ...additions.filter(text => text.length > 0)].join('\n\n');
  const actualCharacters = Array.from(finalText).length;
  const countFooter = finalText.match(/[（(](?:全文|共|字数)\s*(\d+)(?:个)?(?:字|字符)[^）)]*[）)]\s*$/u);
  if (countFooter && (countReportRequested !== true || Number(countFooter[1]) !== actualCharacters))
    return { status: countReportRequested === true ? 'self_reported_count_mismatch' : 'unrequested_verification_footer',
      actualCharacters, maxCharacters, readyForDelivery: false, outputText: null, truncated: false };
  const readyForDelivery = actualCharacters <= maxCharacters;
  return { status: readyForDelivery ? 'final_answer_within_budget' : 'final_answer_revision_required',
    actualCharacters, maxCharacters, remainingCharacters: maxCharacters - actualCharacters,
    readyForDelivery, outputText: readyForDelivery ? finalText : null, truncated: false };
}
