// Explicit local file workflow. No background queue, automatic upload or shell execution.
import { open, lstat } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createStrategyClient, parseJsonStrict, prepareFeedback, validateFeedbackRecord, withdrawFeedback, STRATEGY_CONTRACT } from './strategy-client.mjs';

async function readJson(path) {
  const stat = await lstat(path);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size > 65536) throw new Error('invalid_local_file');
  const file = await open(path, 'r');
  try {
    const buffer = Buffer.alloc(65537);
    const { bytesRead } = await file.read(buffer, 0, buffer.length, 0);
    if (bytesRead > 65536) throw new Error('local_file_too_large');
    return parseJsonStrict(new TextDecoder('utf-8', { fatal: true }).decode(buffer.subarray(0, bytesRead)));
  } finally { await file.close(); }
}

async function writeNew(path, value) {
  const file = await open(path, 'wx', 0o600);
  try { await file.writeFile(JSON.stringify(value, null, 2) + '\n', 'utf8'); await file.sync(); }
  finally { await file.close(); }
}

export async function runFileCommand(args, clientOptions = {}) {
  const [command, ...rest] = args;
  if (!['prepare','send','withdraw'].includes(command) || rest.length % 2) throw new Error('invalid_arguments');
  const opts = {};
  for (let i = 0; i < rest.length; i += 2) {
    if (!['--in','--out','--metrics','--consent','--target'].includes(rest[i]) || Object.hasOwn(opts, rest[i])) throw new Error('invalid_arguments');
    opts[rest[i]] = rest[i + 1];
  }
  const keys = Object.keys(opts).sort().join(',');
  const expected = command === 'prepare' ? '--in,--metrics,--out' : command === 'withdraw' ? '--in,--out' : '--consent,--in,--out,--target';
  if (keys !== expected || !opts['--in'] || !opts['--out'] || resolve(opts['--in']) === resolve(opts['--out'])) throw new Error('invalid_arguments');
  const input = await readJson(opts['--in']);
  if (command === 'prepare') {
    const record = prepareFeedback(input, await readJson(opts['--metrics']));
    await writeNew(opts['--out'], record);
    return { status: 'prepared', send_attempted: false };
  }
  if (command === 'withdraw') {
    await writeNew(opts['--out'], withdrawFeedback(input));
    return { status: 'withdrawn_locally', send_attempted: false, server_deletion: false };
  }
  if (opts['--consent'] !== 'yes') throw new Error('explicit_consent_required');
  if (!['production','development'].includes(opts['--target'])) throw new Error('explicit_target_required');
  const baseUrl = opts['--target'] === 'production' ? STRATEGY_CONTRACT.baseUrl : STRATEGY_CONTRACT.developmentBaseUrl;
  const record = validateFeedbackRecord(input);
  if (record.binding.base_url !== baseUrl) throw new Error('feedback_endpoint_mismatch');
  if (!['prepared','outcome_unknown'].includes(record.status)) throw new Error('feedback_not_sendable');
  // Both artifacts are reserved BEFORE the network call. The attempt is a durable
  // same-body recovery record even if the process dies or saving the result fails.
  const pending = { ...record, status: 'outcome_unknown', result_code: 'outcome_unknown' };
  await writeNew(opts['--out'], pending);
  const resultFile = await open(opts['--out'] + '.result.json', 'wx', 0o600);
  try {
    const client = createStrategyClient({ ...clientOptions, baseUrl });
    const outcome = await client.sendPreparedFeedback(record, { consent: true });
    const { send_attempted, ...saved } = outcome;
    await resultFile.writeFile(JSON.stringify(saved, null, 2) + '\n', 'utf8'); await resultFile.sync();
    return { status: saved.status, result_code: saved.result_code, send_attempted };
  } finally { await resultFile.close(); }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try { console.log(JSON.stringify(await runFileCommand(process.argv.slice(2)))); }
  catch { console.error(JSON.stringify({ status: 'not_completed', instruction: 'Keep the original and any attempt file; inspect the latest valid receipt before retrying. No automatic resend.' })); process.exitCode = 2; }
}
