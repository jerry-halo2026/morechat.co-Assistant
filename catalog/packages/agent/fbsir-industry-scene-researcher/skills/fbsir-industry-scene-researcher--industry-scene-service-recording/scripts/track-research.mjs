import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { canonicalJSON, validateSchema } from './research-kernel.mjs';

const CARD_IDS = ['smart-hardware-service-triage', 'smart-hardware-quality-review', 'smart-hardware-edge-interaction'];
const TOP_KEYS = ['schema', 'record_id', 'record_version', 'brief_binding', 'state', 'selection', 'demand_snapshot', 'supply_snapshot', 'fit_matrix', 'coverage', 'decision_log', 'supersedes'];
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

export class TrackResearchError extends Error {
  constructor(code, message, errors = []) {
    super(message);
    this.name = 'TrackResearchError';
    this.code = code;
    this.errors = errors;
  }
}

function fail(code, message) {
  throw new TrackResearchError(code, message);
}

function plain(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value) && [Object.prototype, null].includes(Object.getPrototypeOf(value));
}

function exactKeys(value, keys, code) {
  if (!plain(value)) fail(code, 'Expected a plain object');
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) fail(code, 'Fields do not match the closed local contract');
}

function safeReference(reference) {
  const value = reference.source_id;
  if (/^[a-z][a-z0-9+.-]*:/i.test(value) || value.startsWith('/') || value.startsWith('\\') || value.includes('..') || value.includes('\\')) {
    return false;
  }
  return true;
}

function briefSha256(brief) {
  if (!plain(brief)) fail('invalid_brief', 'ResearchBrief must be a plain local object');
  return createHash('sha256').update(canonicalJSON(brief), 'utf8').digest('hex');
}

function clone(value) {
  return structuredClone(value);
}

export function loadMethodCards() {
  const document = JSON.parse(readFileSync(new URL('../templates/smart-hardware-method-cards.json', import.meta.url), 'utf8'));
  if (!plain(document) || document.schema !== 'research.track-method-cards/v1' || document.synthetic !== true || !Array.isArray(document.cards)) {
    fail('invalid_method_cards', 'Bundled method cards must be an explicit synthetic local document');
  }
  if (document.cards.length !== CARD_IDS.length || document.cards.some((card, index) => card.track_id !== CARD_IDS[index] || card.synthetic !== true || card.performance_claims !== 'none')) {
    fail('invalid_method_cards', 'The three bundled cards must remain ordered, synthetic, and free of performance claims');
  }
  return clone(document.cards);
}

export function validateTrackResearch(record) {
  const structural = validateSchema(record, 'track-research.schema.json');
  if (!structural.valid) return { ...structural, networkCalled: false, globalTrackCreated: false };
  const errors = [];
  const add = (path, code, message) => errors.push({ path, code, message });
  const supplies = new Set();
  for (const [index, supply] of record.supply_snapshot.entries()) {
    if (supplies.has(supply.supply_id)) add(`$/supply_snapshot/${index}`, 'duplicate_supply_id', 'Supply IDs must be unique');
    supplies.add(supply.supply_id);
  }
  const fits = new Set();
  for (const [index, fit] of record.fit_matrix.entries()) {
    if (fits.has(fit.fit_id)) add(`$/fit_matrix/${index}`, 'duplicate_fit_id', 'Fit IDs must be unique');
    fits.add(fit.fit_id);
    if (!supplies.has(fit.supply_id)) add(`$/fit_matrix/${index}/supply_id`, 'fit_supply_missing', 'Fit must reference a local supply snapshot');
    if (fit.status === 'conflict' && fit.support_refs.length + fit.counter_refs.length === 0) add(`$/fit_matrix/${index}`, 'conflict_evidence_missing', 'Conflict requires at least one supporting or counter reference');
  }
  const facts = [...Object.entries(record.demand_snapshot), ...record.supply_snapshot.flatMap((supply) => ['relation', 'evidence', 'applicability', 'method', 'availability'].map((key) => [key, supply[key]]))];
  for (const [name, fact] of facts) {
    if (fact.status === 'known' && (typeof fact.value_text !== 'string' || fact.value_text.length === 0 || fact.origin === 'unknown')) add(`$/facts/${name}`, 'known_fact_invalid', 'Known facts require text and a non-unknown origin');
    if (['unknown', 'withheld', 'conflict'].includes(fact.status) && fact.value_text !== null) add(`$/facts/${name}`, 'non_known_value_preserved_incorrectly', 'Unknown, withheld, and conflict projections use null local value_text; details remain in refs and fit records');
    if (['unknown', 'withheld'].includes(fact.status) && fact.origin !== 'unknown') add(`$/facts/${name}`, 'unknown_origin_invalid', 'Unknown and withheld require unknown origin');
  }
  const visitReferences = (value, path = '$') => {
    if (Array.isArray(value)) return value.forEach((item, index) => visitReferences(item, `${path}/${index}`));
    if (!plain(value)) return;
    if (Object.keys(value).length === 2 && Object.hasOwn(value, 'source_id') && Object.hasOwn(value, 'source_version') && !safeReference(value)) add(path, 'unsafe_local_reference', 'References must be project-relative IDs or paths, not URLs, absolute paths, traversal, or commands');
    for (const [key, child] of Object.entries(value)) visitReferences(child, `${path}/${key}`);
  };
  visitReferences(record);
  for (const [name, metric] of Object.entries(record.coverage)) {
    if (metric.status === 'known' && metric.value === null) add(`$/coverage/${name}`, 'known_metric_missing', 'Known metrics require an observed value');
    if (metric.status === 'unknown' && metric.value !== null) add(`$/coverage/${name}`, 'unknown_metric_filled', 'Unknown metrics retain null');
  }
  if (record.selection === null && record.state !== 'needs_selection') add('$/state', 'selection_state_invalid', 'A null selection requires needs_selection');
  if (record.selection !== null && record.state === 'needs_selection') add('$/state', 'selection_state_invalid', 'A selected record cannot be needs_selection');
  return { valid: errors.length === 0, errors, warnings: [], networkCalled: false, globalTrackCreated: false };
}

function requireValid(record) {
  const result = validateTrackResearch(record);
  if (!result.valid) throw new TrackResearchError('invalid_track_research', 'Track sidecar failed closed validation', result.errors);
}

const AUTOMATIC_TRACK_NEGATION = /(?:不做|不研究|不看|不要|不是|排除|不考虑|拒绝|避开|别做)[^，。；,.!?;！？\n]{0,6}$/;

function automaticTrackExplicitlyExcluded(text, card) {
  return card.keywords.some((keyword) => {
    let offset = 0;
    while (offset < text.length) {
      const index = text.indexOf(keyword, offset);
      if (index < 0) return false;
      if (AUTOMATIC_TRACK_NEGATION.test(text.slice(Math.max(0, index - 16), index))) return true;
      offset = index + keyword.length;
    }
    return false;
  });
}

export function selectTrack({ text, explicitTrackId = null, customTrack = null } = {}) {
  if (typeof text !== 'string' || !text.trim()) fail('invalid_track_query', 'A non-empty local research question is required');
  if (explicitTrackId !== null && typeof explicitTrackId !== 'string') fail('invalid_track_id', 'Explicit track ID must be a string or null');
  if (customTrack !== null) {
    exactKeys(customTrack, ['track_id', 'track_version', 'title'], 'invalid_custom_track');
    if (!/^[a-z][a-z0-9-]{2,95}$/.test(customTrack.track_id) || !Number.isSafeInteger(customTrack.track_version) || customTrack.track_version < 1 || typeof customTrack.title !== 'string' || !customTrack.title.trim()) fail('invalid_custom_track', 'Custom track must remain a valid local user proposal');
  }
  const cards = loadMethodCards();
  const candidates = [...cards, ...(customTrack ? [{ ...customTrack, origin: 'user_proposed', decision: customTrack.title, demand_focus: [], supply_checks: [], deliverables: [], keywords: [] }] : [])];
  const explicit = explicitTrackId === null ? null : candidates.find((card) => card.track_id === explicitTrackId);
  if (explicitTrackId !== null && !explicit) fail('unknown_track_id', 'Explicit track must be bundled or an explicit local user proposal');
  const automaticCards = explicit ? cards : cards.filter((card) => !automaticTrackExplicitlyExcluded(text, card));
  const matched = explicit ? [explicit] : automaticCards.filter((card) => card.keywords.some((keyword) => text.includes(keyword)));
  if (matched.length === 1) {
    const card = matched[0];
    const selection = {
      track_id: card.track_id,
      track_version: card.track_version,
      origin: card.origin === 'user_proposed' ? 'user_proposed' : 'bundled_method',
      selection_basis: explicit ? 'user_explicit' : 'unambiguous_non_mutating_rule',
      evidence_refs: []
    };
    return { state: 'current', selection, firstValue: { decision: card.decision, demand_focus: card.demand_focus, supply_checks: card.supply_checks, deliverables: card.deliverables }, suggestions: [], synthetic_method: true, globalTrackCreated: false };
  }
  return {
    state: 'needs_selection',
    selection: null,
    firstValue: { branches: automaticCards.map((card) => ({ track_id: card.track_id, title: card.title, decision: card.decision })), unknown_preserved: true },
    suggestions: automaticCards.slice(0, 2).map((card) => ({ track_id: card.track_id, status: 'suggested_unaccepted', text: `如你的实际问题是“${card.decision}”，可明确选择${card.title}。` })),
    synthetic_method: true,
    globalTrackCreated: false
  };
}

function projectFact(fact, allowed) {
  if (fact.status === 'conflict') return { value: 'unknown', origin: 'derived', status: 'conflict', evidence_version: null };
  if (fact.status !== 'known' || !allowed.has(fact.value_text)) return { value: 'unknown', origin: 'unknown', status: 'unknown', evidence_version: null };
  return { value: fact.value_text, origin: fact.origin === 'user_explicit' ? 'user_explicit' : 'derived', status: 'known', evidence_version: null };
}

export function projectTrackToIntent(record, supplyId) {
  requireValid(record);
  const supply = record.supply_snapshot.find((item) => item.supply_id === supplyId);
  if (!supply) fail('supply_not_found', 'Projection requires a supply from the local sidecar');
  return {
    demand: {
      goal: projectFact(record.demand_snapshot.goal, DEMAND_ENUMS.goal),
      context: projectFact(record.demand_snapshot.context, DEMAND_ENUMS.context),
      constraints: projectFact(record.demand_snapshot.constraints, DEMAND_ENUMS.constraints)
    },
    supply: {
      relation: projectFact(supply.relation, SUPPLY_ENUMS.relation),
      evidence: projectFact(supply.evidence, SUPPLY_ENUMS.evidence),
      applicability: projectFact(supply.applicability, SUPPLY_ENUMS.applicability)
    }
  };
}

export function reconcileTrackResearch(previous, changes) {
  requireValid(previous);
  if (!plain(changes)) fail('invalid_track_changes', 'Track changes must be an object');
  const allowed = new Set(['nextBrief', 'nextBriefVersion', 'nextIntentRevision', 'selection', 'changedSupplyIds', 'supplyVersionUpdates', 'changedSourceIds', 'observedAt', 'action', 'accepted']);
  if (Object.keys(changes).some((key) => !allowed.has(key))) fail('invalid_track_changes', 'Unknown track change field');
  for (const key of ['changedSupplyIds', 'changedSourceIds']) if (changes[key] !== undefined && (!Array.isArray(changes[key]) || changes[key].some((item) => typeof item !== 'string'))) fail('invalid_track_changes', `${key} must be a string array`);
  if (typeof changes.observedAt !== 'string' || !changes.observedAt || !['select', 'switch', 'evidence_update', 'review'].includes(changes.action)) fail('invalid_track_changes', 'observedAt and a closed action are required');
  if (changes.accepted !== undefined && typeof changes.accepted !== 'boolean') fail('invalid_track_acceptance', 'Accepted must be an explicit boolean when supplied');
  for (const [key, current] of [['nextBriefVersion', previous.brief_binding.brief_version], ['nextIntentRevision', previous.brief_binding.intent_revision]]) {
    if (changes[key] !== undefined && (!Number.isSafeInteger(changes[key]) || changes[key] < current)) fail('non_monotonic_track_binding', `${key} must be an integer no lower than its predecessor binding`);
  }
  const oldTrack = previous.selection?.track_id ?? null;
  const proposedTrack = changes.selection === undefined ? oldTrack : changes.selection?.track_id ?? null;
  const proposedBriefSha = changes.nextBrief === undefined ? previous.brief_binding.brief_sha256 : briefSha256(changes.nextBrief);
  const selectionChanged = changes.selection !== undefined && canonicalJSON(changes.selection) !== canonicalJSON(previous.selection);
  const briefContentChanged = proposedBriefSha !== previous.brief_binding.brief_sha256;
  const intentScopeChanged = changes.nextIntentRevision !== undefined && changes.nextIntentRevision > previous.brief_binding.intent_revision;
  const decisionRequested = ['select', 'switch'].includes(changes.action) || selectionChanged || briefContentChanged || intentScopeChanged;
  if (decisionRequested && changes.accepted === undefined) fail('track_acceptance_required', 'Actual selection, Brief content, or intent scope changes require explicit acceptance');
  const acceptedDecision = decisionRequested && changes.accepted === true;
  const next = clone(previous);
  const nextTrack = acceptedDecision && selectionChanged ? proposedTrack : oldTrack;
  const trackChanged = oldTrack !== nextTrack;
  const changedSupplies = new Set([...(changes.changedSupplyIds ?? []), ...Object.keys(changes.supplyVersionUpdates ?? {})]);
  const changedSources = new Set(changes.changedSourceIds ?? []);
  next.record_version += 1;
  next.record_id = `${previous.record_id}-r${next.record_version}`;
  next.supersedes = { record_id: previous.record_id, record_version: previous.record_version, sha256: createHash('sha256').update(canonicalJSON(previous), 'utf8').digest('hex') };
  if (acceptedDecision && briefContentChanged) next.brief_binding.brief_sha256 = proposedBriefSha;
  if (changes.nextBriefVersion !== undefined && (!decisionRequested || acceptedDecision)) next.brief_binding.brief_version = changes.nextBriefVersion;
  if (acceptedDecision && intentScopeChanged) next.brief_binding.intent_revision = changes.nextIntentRevision;
  if (acceptedDecision && selectionChanged) next.selection = clone(changes.selection);
  for (const supply of next.supply_snapshot) {
    if (Object.hasOwn(changes.supplyVersionUpdates ?? {}, supply.supply_id)) supply.supply_version = changes.supplyVersionUpdates[supply.supply_id];
  }
  for (const fit of next.fit_matrix) {
    const refs = [...fit.support_refs, ...fit.counter_refs];
    const affected = changedSupplies.has(fit.supply_id) || refs.some((ref) => changedSources.has(ref.source_id)) || (trackChanged && fit.track_id === oldTrack);
    if (affected) fit.derivation_status = fit.user_edit_text === null ? 'stale' : 'needs_review';
  }
  next.state = next.selection === null ? 'needs_selection' : next.fit_matrix.some((fit) => fit.derivation_status !== 'current') ? 'stale' : 'current';
  const details = acceptedDecision
    ? '本地明确采纳用户决定；只标相关fit失效，保留手改、未受影响证据与前驱。'
    : decisionRequested
      ? '建议未明确采纳；选择、Brief及意图绑定保持前驱，仅续接明确证据变化。'
      : '纯证据或复核续接；未记录用户采纳决定，只标相关fit失效并保留前驱。';
  next.decision_log.push({ record_version: next.record_version, action: changes.action, track_id: nextTrack, accepted: acceptedDecision, observed_at: changes.observedAt, details });
  requireValid(next);
  return next;
}

export function applyTrackSelection(previous, { accepted, selection, nextBrief, intentScopeChange = false, briefVersionChange = false, observedAt } = {}) {
  requireValid(previous);
  if (typeof accepted !== 'boolean') fail('invalid_track_acceptance', 'Accepted must be an explicit boolean');
  for (const [name, value] of [['intentScopeChange', intentScopeChange], ['briefVersionChange', briefVersionChange]]) {
    if (typeof value !== 'boolean') fail('invalid_track_change_flag', `${name} must be an explicit boolean`);
  }
  if (!accepted) return clone(previous);
  if (!plain(selection) || !plain(nextBrief) || typeof observedAt !== 'string' || !observedAt) fail('invalid_track_acceptance', 'Accepted selection requires selection, nextBrief, and observedAt');
  const acceptedSelection = { ...clone(selection), selection_basis: 'user_explicit' };
  return reconcileTrackResearch(previous, {
    nextBrief,
    nextBriefVersion: previous.brief_binding.brief_version + (briefVersionChange ? 1 : 0),
    nextIntentRevision: previous.brief_binding.intent_revision + (intentScopeChange ? 1 : 0),
    selection: acceptedSelection,
    observedAt,
    accepted: true,
    action: previous.selection?.track_id === selection.track_id ? 'select' : 'switch'
  });
}

export function validateTrackTopLevelShape(record) {
  exactKeys(record, TOP_KEYS, 'invalid_track_top_level');
  return true;
}
