// Relations for already schema-checked, caller-supplied records. No search, file writes or truth certification.
const text = value => typeof value === 'string' && value.trim().length > 0;
const direct = new Set(['source_fact', 'company_claim', 'independent_observation', 'user_statement']);
const TRACKING_KEYS = new Set(['utm_source','utm_medium','utm_campaign','utm_term','utm_content','utm_id','gclid','fbclid']);
function referenceKey(reference) {
  if (!text(reference)) return null;
  const value = reference.trim();
  if (!/^https?:\/\//i.test(value)) return 'label:' + value;
  try {
    const url = new URL(value);
    if (url.username || url.password) return null;
    // Preserve content query bytes/order. Remove only explicitly reviewed tracking keys.
    const originalQuery = url.search;
    const query = (originalQuery ? originalQuery.slice(1).split('&') : []).filter(part => {
      if (!part) return true;
      let key = part.split('=',1)[0];
      try { key = decodeURIComponent(key.replaceAll('+',' ')); } catch { return true; }
      return !TRACKING_KEYS.has(key.toLowerCase());
    });
    const filteredQuery = query.length ? '?' + query.join('&') : '';
    if (filteredQuery !== originalQuery) url.search = filteredQuery;
    // Ordinary document anchors identify the same source. Hash routes may identify another article.
    if (!/[/?=]/.test(url.hash)) url.hash = '';
    return 'url:' + url.href;
  } catch { return null; }
}
function preciseTextSignals(value) {
  const datePattern=/(?:^|[^\d])((?:\d{4})[-/]\d{1,2}[-/]\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日)/g;
  const dates = [...value.matchAll(datePattern)].map(m=>m[1]);
  const withoutFullDates=value.replace(datePattern,' ');
  const ambiguousShort=/\b\d{1,2}\s*\/\s*\d{1,2}\b/.test(withoutFullDates);
  const percent = /%|％|百分之|百分比|百分点|\bpercent(?:age)?(?:\s+points?)?\b/i.test(value);
  const quantity = /[+-]?\d[\d,]*(?:\.\d+)?\s*(?:%|％|万|亿|兆|千|百|人|台|次|单|元|美元|条|家|件|套|个|名|小时|分钟|秒|页|\b(?:million|billion|thousand|users?|downloads?|installs?|people|percent(?:age)?)\b)/i.test(value);
  return { dates, percent, quantity, ambiguousShort };
}

export function checkClaimsRelations(brief, claims) {
  const errors = [], warnings = [], ids = new Map(), families = new Set(), sources = new Map(), readSources = new Set(), referenceFamilies = new Map();
  const add = (id, code, message) => errors.push({ path: '$/claims/' + id, code, message });
  if (!text(brief.question)) errors.push({path:'$/brief/question',code:'question_empty',message:'A research question cannot be whitespace.'});
  for (const claim of claims) {
    if (ids.has(claim.id)) add(claim.id, 'duplicate_claim_id', 'Claim IDs must be unique.');
    ids.set(claim.id, claim);
  }
  for (const claim of claims) {
    const current = claim.status === 'current', anchored = claim.evidence.every(e => e.readStatus === 'content_read' && text(e.anchor));
    const isDirect = direct.has(claim.evidenceLevel);
    const signals = preciseTextSignals(claim.text);
    if (!text(claim.id) || !text(claim.text)) add(claim.id,'claim_identity_or_text_empty','Claim identity and text cannot be whitespace.');
    if (!current) add(claim.id, 'invalidated_claim_cannot_support_delivery', 'Recheck changed evidence before presenting this as current.');
    if (isDirect && (!claim.evidence.length || !anchored)) add(claim.id, 'direct_claim_requires_read_anchor', 'Direct evidence needs actually observed content and a locatable anchor.');
    for (const source of claim.evidence) {
      const reference = referenceKey(source.reference);
      if (!text(source.sourceId) || !text(source.familyId) || reference === null)
        add(claim.id,'source_identity_or_reference_empty','Source ID, family and usable reference must be nonempty; credentials are not source references.');
      if (reference !== null) {
        if (referenceFamilies.has(reference) && referenceFamilies.get(reference) !== source.familyId)
          add(claim.id,'same_reference_split_source_families','The same source reference cannot create independent families by changing source IDs.');
        referenceFamilies.set(reference,source.familyId);
      }
      if (brief.allowedSourceIds && !brief.allowedSourceIds.includes(source.sourceId)) add(claim.id, 'source_outside_selected_scope', 'Source is not in the user-selected source set.');
      const fingerprint = JSON.stringify([source.familyId, source.reference, source.sourceRole]);
      if (sources.has(source.sourceId) && sources.get(source.sourceId) !== fingerprint) add(claim.id, 'source_identity_conflict', 'One source ID cannot carry different provenance.');
      sources.set(source.sourceId, fingerprint);
      if (source.readStatus === 'content_read' && text(source.anchor)) { families.add(source.familyId); readSources.add(source.sourceId); }
      if (claim.evidenceLevel === 'source_fact' && ['media_reporting','community_self_report','company_self_report'].includes(source.sourceRole) && claim.assertionScope !== 'reported_content')
        add(claim.id, 'reported_source_not_underlying_fact', 'A read report proves what was reported, not automatically the underlying outcome.');
      if (claim.evidenceLevel === 'company_claim' && source.sourceRole !== 'company_self_report') add(claim.id, 'company_claim_source_mismatch', 'Company self-report needs an identified company source.');
      if (claim.evidenceLevel === 'user_statement' && source.sourceRole !== 'user_supplied') add(claim.id, 'user_statement_source_mismatch', 'A media/community author is not the current user.');
    }
    if (claim.evidenceLevel === 'independent_observation' && (!text(claim.methodSummary) || !claim.evidence.some(e => e.sourceRole === 'independent_observation')))
      add(claim.id, 'independent_method_not_recorded', 'An independent method and observation source must be recorded.');
    if (claim.evidenceLevel === 'inference' && !text(claim.methodSummary)) add(claim.id, 'inference_reasoning_missing', 'State the reasoning and its limits.');
    if (['unknown','hypothesis'].includes(claim.evidenceLevel) && !(claim.limitations || []).some(text)) add(claim.id, 'unknown_boundary_missing', 'State what is unknown or what would test the hypothesis.');
    if (isDirect && ['numeric','date','verbatim_quote'].includes(claim.assertionKind) && !anchored)
      add(claim.id, 'hard_claim_original_anchor_missing', 'Search snippets do not support precise figures, dates or quotations.');
    if (isDirect && claim.assertionKind === 'numeric') {
      if (![claim.subject, claim.period, claim.unit].every(text)) add(claim.id, 'numeric_context_missing', 'A figure needs its subject, period and unit.');
      if ((signals.percent || /%|％|百分比|率|比例|percent|ratio/i.test(claim.unit || '')) && !text(claim.denominator)) add(claim.id, 'numeric_denominator_missing', 'A rate needs its denominator or explicit unknown status.');
      if (signals.percent) {
        const percentagePoints=/百分点|percentage\s+points?/i.test(claim.text);
        const compatible=percentagePoints ? /^(?:百分点|percentage[ _-]?points?)$/i.test((claim.unit||'').trim()) : /^(?:%|％|百分比|百分率|百分数|percent|percentage)$/i.test((claim.unit||'').trim());
        if (!compatible) add(claim.id,'numeric_text_unit_conflict','A percentage in the text cannot be reclassified by an unrelated unit.');
      }
    }
    if (isDirect && claim.assertionKind === 'date' && (!text(claim.subject) || !claim.dateKind || claim.dateKind === 'unknown'))
      add(claim.id, 'date_role_missing', 'Publication, announcement, effective and event dates are distinct.');
    if (isDirect && claim.assertionKind === 'date') {
      const date = typeof claim.dateValue === 'string' ? new Date(claim.dateValue + 'T00:00:00Z') : null;
      if (!date || !Number.isFinite(date.getTime()) || date.toISOString().slice(0,10) !== claim.dateValue || claim.dateValue.startsWith('0000'))
        add(claim.id, 'exact_date_value_invalid', 'Use an actual calendar date; uncertain dates remain unknown.');
    }
    if (claim.assertionKind === 'verbatim_quote' && isDirect && (!text(claim.exactQuote) || !claim.evidence.some(e => e.readStatus === 'content_read' && typeof e.excerpt === 'string' && e.excerpt.includes(claim.exactQuote))))
      add(claim.id, 'exact_quote_not_in_observed_excerpt', 'Exact quotation must occur in a read excerpt, with attribution.');
    if (claim.assertionKind === 'causal' && isDirect && (claim.causalDesignObserved !== true || !text(claim.methodSummary)))
      add(claim.id, 'causal_design_not_recorded', 'Attribution records do not prove a causal effect.');
    if (claim.assertionKind === 'descriptive' && signals.quantity)
      add(claim.id, 'quantified_text_requires_numeric_review', 'This quantified statement needs explicit numeric context review.');
    if (signals.dates.length && !['date','verbatim_quote'].includes(claim.assertionKind))
      add(claim.id,'precise_date_text_requires_date_review','A precise date in the text needs an explicit date role or an attributed exact quotation.');
    if (signals.ambiguousShort) {
      if (!['unknown','hypothesis'].includes(claim.evidenceLevel))
        add(claim.id,'ambiguous_short_date_or_fraction_requires_review','A short slash form may be a date, ratio or other label; disambiguate against the source without guessing.');
      else warnings.push({path:'$/claims/'+claim.id,code:'ambiguous_short_form_unresolved',message:'The slash form remains explicitly unverified; no date or ratio was inferred.'});
    }
    for (const parent of claim.derivedFromClaimIds || []) {
      if (!ids.has(parent)) add(claim.id, 'claim_dependency_missing', 'A dependency is not present.');
      else if (parent === claim.id || ids.get(parent).status !== 'current') add(claim.id, 'claim_dependency_not_current', 'Do not reuse self-dependent or invalidated evidence.');
    }
  }
  const active = new Set(), done = new Set();
  function visit(id) {
    if (active.has(id)) { add(id, 'claim_dependency_cycle', 'Claim dependencies must be acyclic.'); return; }
    if (done.has(id)) return;
    active.add(id);
    for (const parent of ids.get(id)?.derivedFromClaimIds || []) if (ids.has(parent)) visit(parent);
    active.delete(id); done.add(id);
  }
  for (const id of ids.keys()) visit(id);
  if (brief.declaredSourceFamilyCount !== undefined && brief.declaredSourceFamilyCount !== families.size)
    errors.push({ path: '$/brief/declaredSourceFamilyCount', code: 'source_family_count_mismatch', message: 'Reposts, extracts and translations from one family count once.' });
  const coverage = brief.queryCoverage || [];
  if (new Set(coverage.map(c => c.axis)).size !== coverage.length) errors.push({ path:'$/brief/queryCoverage', code:'duplicate_query_axis', message:'One coverage state per similarity axis.' });
  for (const row of coverage) {
    if (row.status === 'sources_read' && (!(row.sourceIds || []).length || row.sourceIds.some(id => !readSources.has(id))))
      errors.push({ path:'$/brief/queryCoverage', code:'query_read_sources_missing', message:'Read coverage needs sources present in the claim set.' });
    if (['not_run','blocked'].includes(row.status)) warnings.push({ path:'$/brief/queryCoverage', code:'query_coverage_incomplete', message:row.axis + ': ' + row.reason });
  }
  const reviewRequired = errors.some(e => ['quantified_text_requires_numeric_review','precise_date_text_requires_date_review','numeric_text_unit_conflict','ambiguous_short_date_or_fraction_requires_review'].includes(e.code));
  return { valid: errors.length === 0, status:errors.length ? (reviewRequired?'needs_review':'record_checks_failed') : 'record_checks_passed', reviewRequired,
    errors, warnings, claimCount: claims.length,
    sourceCount: sources.size, distinctReadSourceFamilies: errors.some(e=>['same_reference_split_source_families','source_identity_or_reference_empty'].includes(e.code)) ? null : families.size,
    textSignalCoverage: 'supported_precise_forms_not_complete_nlp',
    evidenceStatus: 'data_checked', sourceAuthenticityVerified: false, semanticTruthCertified: false,
    queryCoverageObservedByHelper: false, bundleMigrationPerformed: false, networkCalled: false };
}

/** Checks only explicit records; actual host read-back must still be observed separately. */
export function assessDeliveryRecords(validation, claims, delivery) {
  const own = (o,k) => Object.hasOwn(o,k), plain = o => o && typeof o === 'object' && !Array.isArray(o) && [Object.prototype,null].includes(Object.getPrototypeOf(o));
  const invalid = { readyForDelivery: false, status:'delivery_records_invalid', gates:[], unmetItems:[], hostExecutionProven:false };
  if (!plain(delivery) || !Array.isArray(delivery.requestedFormats) || !delivery.requestedFormats.every(text) ||
      !Array.isArray(delivery.artifacts) || !Array.isArray(delivery.unmetItems) || !delivery.unmetItems.every(text) ||
      !Array.isArray(delivery.visibleEvidenceClaimIds) || !delivery.visibleEvidenceClaimIds.every(text)) return invalid;
  const allowed = new Set(['requestedFormats','artifacts','unmetItems','visibleEvidenceClaimIds']);
  if (Object.keys(delivery).some(k => !allowed.has(k))) return invalid;
  const artifacts = delivery.artifacts;
  const fields = new Set(['format','kind','status','artifactId','finalSha256','readbackSha256','readbackRef']);
  if (!artifacts.every(a => plain(a) && Object.keys(a).every(k=>fields.has(k)) && text(a.format) &&
      ['chat','file'].includes(a.kind) && ['not_run','created','read_back','presented'].includes(a.status))) return invalid;
  const gates = [
    { id:'traceable_claims', passed:validation.valid },
    { id:'source_family_deduplication', passed:!validation.errors.some(e=>['source_family_count_mismatch','source_identity_conflict','same_reference_split_source_families','source_identity_or_reference_empty'].includes(e.code)) },
    { id:'uncertainty_visible', passed:claims.every(c => delivery.visibleEvidenceClaimIds.includes(c.id)) }
  ];
  const formatKey = value => ({md:'markdown',txt:'text',plain_text:'text'}[value.trim().toLowerCase().replace(/^\./,'')] || value.trim().toLowerCase().replace(/^\./,''));
  const fileFormats = new Set(['pdf','docx','doc','pptx','ppt','xlsx','xls','csv','html','htm','png','jpg','jpeg','svg','gif','webp','audio','video','mp3','mp4','wav','webm','zip']);
  const chatFormats = new Set(['chat','text','markdown','json']);
  const compatible = artifact => artifact.kind==='file' || (!fileFormats.has(formatKey(artifact.format)) && chatFormats.has(formatKey(artifact.format)));
  const artifactIssues = artifacts.filter(a=>!compatible(a)).map(a=>({format:a.format,code:'artifact_kind_format_conflict'}));
  const files = artifacts.filter(a=>a.kind==='file' || fileFormats.has(formatKey(a.format)));
  const digest = value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
  const filesRead = files.every(a => a.kind==='file' && ['read_back','presented'].includes(a.status) && text(a.artifactId) && text(a.readbackRef) &&
    digest(a.finalSha256) && own(a,'readbackSha256') && a.finalSha256===a.readbackSha256);
  gates.push({ id:'final_file_readback', passed:filesRead, applicability:files.length?'required':'not_applicable' });
  const unmetItems = [...delivery.unmetItems];
  for (const issue of artifactIssues) unmetItems.push('Artifact kind does not fulfill format: '+issue.format);
  for (const format of delivery.requestedFormats) if (!artifacts.some(a=>formatKey(a.format)===formatKey(format) && compatible(a) && (a.kind==='chat' ? a.status==='presented' : ['read_back','presented'].includes(a.status))))
    unmetItems.push('Requested format not completed: ' + format);
  return { readyForDelivery:gates.every(g=>g.passed) && unmetItems.length===0, status:gates.every(g=>g.passed)&&!unmetItems.length?'record_checks_passed':'partial_or_requires_review',
    gates, unmetItems:[...new Set(unmetItems)], artifactIssues, evidenceStatus:'caller_records_checked', hostExecutionProven:false,
    userAcceptanceProven:false, businessValueProven:false, fileReadbackAuthenticatedByHelper:false };
}
