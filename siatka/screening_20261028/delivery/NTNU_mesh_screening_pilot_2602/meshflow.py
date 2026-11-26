"""Mesh-screening controller. Python 3.10+, standard library only.

STAR integration is deliberately gated until a recorded, model-specific adapter
has been validated. No STAR Java API or model object names are guessed here.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid


class ConfigurationError(ValueError):
    pass


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with tmp.open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def require(condition, message):
    if not condition:
        raise ConfigurationError(message)


def evidence(ref):
    return (isinstance(ref, dict) and bool(ref.get('path'))
            and Path(ref['path']).is_file() and digest(ref['path']) == ref.get('sha256'))


def validate_config(cfg, execution=False):
    require(cfg.get('schema_version') == 1, 'Unsupported configuration schema')
    require(cfg.get('target_version') == '21.02.007', 'Target must be 21.02.007')
    require(cfg.get('precision') == 'double', 'Double precision is required')
    require(cfg.get('baseline_verified') is True, 'Baseline model has not been inspected')
    require(evidence(cfg.get('inventory')), 'Missing or changed model inventory evidence')
    require(bool(re.fullmatch('[a-f0-9]{64}', cfg.get('locked_settings_sha256', ''))),
            'Missing locked geometry/physics/prism-settings fingerprint')
    params = cfg.get('parameters', [])
    require(1 <= len(params) <= 5, 'Screen 1–5 verified independent parameters initially')
    names = [p.get('name') for p in params]
    require(len(set(names)) == len(names), 'Duplicate parameter name')
    for p in params:
        require(bool(re.fullmatch('[a-z][a-z0-9_]*', p.get('name', ''))), 'Invalid parameter name')
        require(p.get('unit') == 'm', 'Controller inputs use absolute metres')
        require(p.get('independent_verified') is True, 'Parameter dependence has not been audited')
        require(bool(p.get('binding')) and bool(p.get('bounds_basis')), 'Missing control binding or bounds rationale')
        lo, base, hi = p.get('lower'), p.get('baseline'), p.get('upper')
        require(all(number(x) and x > 0 for x in (lo, base, hi)), 'Unverified/nonpositive parameter bounds')
        require(lo <= base <= hi and lo < hi, 'Baseline must lie within a nonzero design interval')
    if not execution:
        return
    require(evidence(cfg.get('baseline')), 'Baseline path/hash unavailable or changed')
    require(evidence(cfg.get('adapter')), 'Recorded STAR adapter unavailable or changed')
    require(evidence(cfg.get('api_validation')), 'Installed STAR API has not been validated')
    require(evidence(cfg.get('launch_validation')), 'STAR batch command has not been validated locally')
    require(cfg.get('mesh_only_verified') is True, 'Adapter is not verified as mesh-only')
    command = cfg.get('command', [])
    require(isinstance(command, list) and all(isinstance(t, str) and t for t in command), 'Command must be an argv list')
    require(bool(command) and Path(command[0]).is_file(), 'Executable path is missing')
    require(any('{baseline}' in t for t in command) and any('{adapter}' in t for t in command),
            'Command must use the isolated baseline and adapter')
    for key in ('case_timeout_s', 'campaign_budget_s', 'min_free_disk_bytes', 'max_cells'):
        require(number(cfg.get(key)) and cfg[key] > 0, f'Missing measured/selected resource limit: {key}')
    require(isinstance(cfg.get('max_consecutive_failures'), int) and cfg['max_consecutive_failures'] > 0,
            'Missing consecutive-failure limit')
    require(cfg.get('quality_rules_verified') is True and bool(cfg.get('quality_rules')),
            'Quality definitions, scopes and thresholds have not been reviewed')
    for rule in cfg['quality_rules']:
        require(rule.get('scope') and rule.get('definition') and rule.get('unit'), 'Incomplete metric definition')
        require(any(k in rule for k in ('min', 'max')), 'Quality rule needs a declared bound')
        for k in ('min', 'max'):
            if k in rule:
                require(number(rule[k]), 'Invalid quality threshold')
    require(bool(cfg.get('objectives')), 'Declare Pareto objectives')
    for obj in cfg['objectives']:
        require(obj.get('direction') in ('min', 'max') and obj.get('name'), 'Invalid objective')


def write_cases(path, rows, names):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='') as stream:
        w = csv.DictWriter(stream, fieldnames=['case_id', 'stage', *names])
        w.writeheader()
        w.writerows(rows)


def load_cases(path, cfg):
    names = [p['name'] for p in cfg['parameters']]
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == ['case_id', 'stage', *names], 'Exact CSV headers/order required')
        rows = list(reader)
    seen = set()
    for row in rows:
        cid = row['case_id']
        require(bool(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,63}', cid or '')), 'Unsafe case ID')
        require(cid not in seen, 'Duplicate case ID')
        seen.add(cid)
        require(row['stage'] in ('pilot', 'doe', 'local'), 'Unknown experiment stage')
        for p in cfg['parameters']:
            try:
                value = float(row[p['name']])
            except (TypeError, ValueError):
                raise ConfigurationError('Missing/nonnumeric case input')
            require(math.isfinite(value) and p['lower'] <= value <= p['upper'], 'Case outside verified bounds')
            row[p['name']] = value
    require(bool(rows), 'No executable cases: baseline inspection is still required')
    return rows


def lhs(parameters, n, seed=20261028, trials=64):
    """Maximin search over seeded Latin hypercubes in log-length coordinates."""
    require(n >= 2, 'LHS requires at least two cases')
    rng = random.Random(seed)
    best, distance = None, -1
    for _ in range(trials):
        axes = []
        for _p in parameters:
            axis = [(i + rng.random()) / n for i in range(n)]
            rng.shuffle(axis)
            axes.append(axis)
        points = list(zip(*axes))
        d = min(sum((a-b)**2 for a, b in zip(points[i], points[j]))
                for i in range(n) for j in range(i))
        if d > distance:
            best, distance = points, d
    return [{p['name']: math.exp(math.log(p['lower']) + x*(math.log(p['upper'])-math.log(p['lower'])))
             for p, x in zip(parameters, point)} for point in best]


def design(cfg, path, stage, n, seed):
    validate_config(cfg)
    params = cfg['parameters']
    if stage == 'pilot':
        require(n == 3, 'First executable pilot must contain three cases')
        # First test isolates one parameter. Others must be checked before wider DoE.
        axis = cfg.get('pilot_parameter')
        require(axis in [p['name'] for p in params], 'Choose a verified pilot parameter')
        p = next(p for p in params if p['name'] == axis)
        candidates = [{q['name']: q['baseline'] for q in params} for _ in range(3)]
        if p['baseline'] == p['lower']:
            candidates[1][axis] = math.sqrt(p['lower'] * p['upper'])
            candidates[2][axis] = p['upper']
        elif p['baseline'] == p['upper']:
            candidates[1][axis] = math.sqrt(p['lower'] * p['upper'])
            candidates[2][axis] = p['lower']
        else:
            candidates[1][axis] = p['lower']
            candidates[2][axis] = p['upper']
    else:
        require(stage == 'doe', 'Local follow-up points need an explicit result-based proposal')
        require(pilot_valid(cfg), 'Review measured pilot and all parameter bindings before generating DoE')
        candidates = lhs(params, n, seed)
    prefix = 'A' if stage == 'pilot' else 'B'
    rows = [dict(case_id=f'{prefix}{i+1:03}', stage=stage, **v) for i, v in enumerate(candidates)]
    write_cases(path, rows, [p['name'] for p in params])


def pilot_valid(cfg):
    """Review artifact is a signed-off technical record, not a CLI override."""
    ref = cfg.get('pilot_review')
    if not evidence(ref):
        return False
    review = read_json(ref['path'])
    refs = review.get('pilot_results', [])
    if not (review.get('decision') == 'proceed'
            and review.get('baseline_sha256') == cfg.get('baseline', {}).get('sha256')
            and review.get('locked_settings_sha256') == cfg.get('locked_settings_sha256')
            and review.get('adapter_sha256') == cfg.get('adapter', {}).get('sha256')
            and review.get('all_parameter_bindings_verified') is True
            and review.get('restart_and_failure_test_verified') is True
            and len(refs) >= 3 and len({r.get('path') for r in refs}) == len(refs)):
        return False
    return all(evidence(r) and read_json(r['path']).get('generation_status') == 'completed'
               and read_json(r['path']).get('contract_status') == 'verified' for r in refs)


def validate_result(result, job, cfg):
    reserved = {'case_fingerprint', 'contract_status', 'attempt_dir', 'process_elapsed_s',
                'quality_status', 'quality_reasons'}
    require(not (reserved & set(result)), 'Adapter overwrote controller-owned metadata')
    for key in ('case_id', 'run_id', 'baseline_sha256'):
        require(result.get(key) == job[key], f'Result identity mismatch: {key}')
    require(result.get('schema_version') == 1, 'Unsupported measurement schema')
    require(result.get('evidence_kind') == 'measured', 'Only actual measured exports may enter campaign results')
    require(result.get('solver_version') == cfg['target_version'], 'STAR build mismatch')
    require(result.get('precision') == cfg['precision'], 'Precision mismatch')
    require(result.get('generation_status') == 'completed', 'No confirmed completed mesh')
    require(result.get('solver_iterations_executed') == 0, 'Mesh-only condition was not confirmed')
    for key in ('readback_before_mesh', 'readback_after_mesh'):
        rb = result.get(key, {})
        require(rb.get('locked_settings_sha256') == cfg['locked_settings_sha256'], 'Prism/physics/geometry settings changed')
        values = rb.get('parameters_m', {})
        require(set(values) == set(job['parameters_m']), 'Parameter readback scope mismatch')
        for name, value in job['parameters_m'].items():
            require(number(values[name]) and math.isclose(values[name], value, rel_tol=1e-9, abs_tol=1e-14),
                    f'Actual mesh-control value mismatch: {name}')
    metrics = result.get('metrics', {})
    for key in ('cell_count', 'mesh_time_s'):
        require(number(metrics.get(key)) and metrics[key] > 0, f'Missing actual metric: {key}')
    require(int(metrics['cell_count']) == metrics['cell_count'], 'Cell count is not an integer')


def quality(result, cfg):
    """Three states. Missing diagnostics cannot become an acceptance."""
    if result.get('generation_status') != 'completed' or result.get('contract_status') != 'verified':
        return 'not_eligible', ['No verified completed mesh']
    metrics = result.get('metrics', {})
    missing, failed = [], []
    for key in ('invalid_cells', 'min_cell_volume_m3'):
        if not number(metrics.get(key)):
            missing.append(key)
    for rule in cfg.get('quality_rules', []):
        value = metrics.get(rule['name'])
        if not number(value):
            missing.append(rule['name'])
        elif ('min' in rule and value < rule['min']) or ('max' in rule and value > rule['max']):
            failed.append(rule['name'])
    if number(metrics.get('min_cell_volume_m3')) and metrics['min_cell_volume_m3'] <= 0:
        failed.append('nonpositive_cell_volume')
    if number(metrics.get('invalid_cells')) and metrics['invalid_cells'] > 0:
        failed.append('invalid_cells')
    if number(metrics.get('cell_count')) and number(cfg.get('max_cells')) and metrics['cell_count'] > cfg['max_cells']:
        failed.append('cell_budget')
    for key in ('prism_review', 'local_resolution_review'):
        review = result.get('reviews', {}).get(key, {})
        if review.get('status') == 'fail':
            failed.append(key)
        elif review.get('status') != 'pass' or not review.get('evidence'):
            missing.append(key)
    if not cfg.get('quality_rules_verified') or not cfg.get('quality_rules'):
        missing.append('verified_quality_policy')
    if failed:
        return 'rejected', failed + ['missing:' + x for x in missing]
    if missing:
        return 'incomplete', missing
    return 'acceptable', []


def pareto(results, cfg):
    objectives = cfg.get('objectives', [])
    if not objectives:
        return set()
    eligible = [r for r in results if quality(r, cfg)[0] == 'acceptable'
                and all(number(r.get('metrics', {}).get(o['name'])) for o in objectives)]
    def vector(r):
        return [r['metrics'][o['name']] * (1 if o['direction'] == 'min' else -1) for o in objectives]
    return {r['case_id'] for r in eligible if not any(
        all(a <= b for a, b in zip(vector(s), vector(r)))
        and any(a < b for a, b in zip(vector(s), vector(r))) for s in eligible)}


def stop_tree(proc):
    if proc.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True, check=False)
    else:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
    proc.wait(timeout=15)


def capture_log(source, destination):
    """Never persist license keys printed by the STAR launcher."""
    pattern = re.compile(rb'(?i)(-podkey\s+)(?:"[^"]*"|\S+)')
    for line in iter(source.readline, b''):
        destination.write(pattern.sub(rb'\1REDACTED', line))
        destination.flush()


def run(cfg, csv_path, root, limit=3, retry=False):
    validate_config(cfg, execution=True)
    rows = load_cases(csv_path, cfg)
    require(isinstance(limit, int) and limit > 0, 'Positive case limit required')
    reviewed = pilot_valid(cfg)
    require(limit <= 3 or reviewed, 'Larger batch requires reviewed measured pilot')
    require(reviewed or all(r['stage'] == 'pilot' for r in rows), 'Initial run is restricted to pilot cases')
    require(reviewed or len(rows) <= 3, 'At most three pilot cases before review')
    root = Path(root).resolve()
    baseline = Path(cfg['baseline']['path']).resolve()
    require(root != baseline.parent and root not in baseline.parents, 'Use a separate campaign directory')
    root.mkdir(parents=True, exist_ok=True)
    # Exclusive directory creation prevents concurrent launchers sharing output.
    lock = root / '.running'
    try:
        lock.mkdir()
    except FileExistsError:
        raise ConfigurationError('Campaign lock exists; inspect processes before removing a stale lock')
    started, count, failures = time.monotonic(), 0, 0
    try:
        stable_cfg = {k: v for k, v in cfg.items() if k != 'pilot_review'}
        for row in rows:
            if count >= limit or time.monotonic()-started >= cfg['campaign_budget_s']:
                break
            if (root / 'STOP').exists():
                break
            require(digest(baseline) == cfg['baseline']['sha256'], 'Baseline changed during campaign')
            require(digest(cfg['adapter']['path']) == cfg['adapter']['sha256'], 'Adapter changed during campaign')
            cid = row['case_id']
            identity = fingerprint({'config': stable_cfg, 'case': row})
            case_root = root / cid
            record = case_root / 'latest.json'
            if record.exists():
                old = read_json(record)
                require(old.get('case_fingerprint') == identity, 'Case/config changed: use a new campaign directory')
                if old.get('generation_status') == 'completed' or not retry:
                    continue
            remaining = cfg['campaign_budget_s'] - (time.monotonic()-started)
            if remaining <= 0:
                break
            require(shutil.disk_usage(root).free >= cfg['min_free_disk_bytes'] + baseline.stat().st_size,
                    'Insufficient disk space for next baseline copy')
            attempt = case_root / ('attempt_' + uuid.uuid4().hex)
            attempt.mkdir(parents=True)
            model = attempt / 'baseline_copy.sim'
            shutil.copy2(baseline, model)
            require(digest(model) == cfg['baseline']['sha256'], 'Baseline-copy checksum mismatch')
            adapter = attempt / Path(cfg['adapter']['path']).name
            shutil.copy2(cfg['adapter']['path'], adapter)
            job = {'schema_version': 1, 'case_id': cid, 'run_id': uuid.uuid4().hex,
                   'stage': row['stage'], 'baseline_sha256': cfg['baseline']['sha256'],
                   'parameters_m': {p['name']: row[p['name']] for p in cfg['parameters']},
                   'locked_settings_sha256': cfg['locked_settings_sha256'],
                   'result_path': str(attempt / 'measurement.json'),
                   'save_sim_path': str(attempt / 'mesh.sim')}
            job_path = attempt / 'job.json'
            atomic_json(job_path, job)
            current = dict(job, case_fingerprint=identity, generation_status='interrupted',
                           contract_status='unverified', metrics={}, attempt_dir=str(attempt),
                           failure_reason='No terminal record yet; inspect this attempt before retry')
            atomic_json(record, current)
            token = {'baseline': str(model), 'adapter': str(adapter), 'workdir': str(attempt)}
            command = [part.format(**token) for part in cfg['command']]
            env = os.environ.copy()
            env['NTNU_MESH_JOB'] = str(job_path)
            proc, stop_campaign, tick = None, False, time.monotonic()
            try:
                with (attempt / 'star.log').open('wb') as log:
                    proc = subprocess.Popen(command, cwd=attempt, env=env, shell=False, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, start_new_session=(os.name != 'nt'))
                    reader = threading.Thread(target=capture_log, args=(proc.stdout, log), daemon=True)
                    reader.start()
                    try:
                        remaining = max(0.01, cfg['campaign_budget_s'] - (time.monotonic()-started))
                        code = proc.wait(timeout=min(cfg['case_timeout_s'], remaining))
                    finally:
                        if proc.poll() is None:
                            stop_tree(proc)
                        reader.join(timeout=15)
                        require(not reader.is_alive(), 'Log stream did not close after process termination')
                        proc.stdout.close()
                require(code == 0, f'STAR process returned {code}')
                result = read_json(job['result_path'])
                validate_result(result, job, cfg)
                current.update(result, generation_status='completed', contract_status='verified', failure_reason='')
                failures = 0
                stop_campaign = result['metrics']['cell_count'] > cfg['max_cells']
            except subprocess.TimeoutExpired:
                stop_tree(proc)
                current.update(generation_status='timeout', failure_reason='Process-tree time limit reached')
                failures += 1
            except KeyboardInterrupt:
                if proc:
                    stop_tree(proc)
                current.update(generation_status='interrupted', failure_reason='Operator interruption')
                stop_campaign = True
            except Exception as exc:
                if proc:
                    stop_tree(proc)
                current.update(generation_status='failed', failure_reason=f'{type(exc).__name__}: {exc}')
                failures += 1
            current['process_elapsed_s'] = time.monotonic()-tick
            current['quality_status'], current['quality_reasons'] = quality(current, cfg)
            atomic_json(attempt / 'record.json', current)
            atomic_json(record, current)
            count += 1
            print(cid, current['generation_status'], current['quality_status'], flush=True)
            require(digest(baseline) == cfg['baseline']['sha256'], 'Baseline changed: stop immediately')
            if stop_campaign or failures >= cfg['max_consecutive_failures']:
                break
    finally:
        lock.rmdir()
    return count


def summarize(cfg, root, output):
    root, output = Path(root), Path(output)
    results = [read_json(p) for p in sorted(root.glob('*/latest.json'))]
    front = pareto(results, cfg)
    output.mkdir(parents=True, exist_ok=True)
    params = [p['name'] for p in cfg.get('parameters', [])]
    metrics = sorted({k for r in results for k in r.get('metrics', {})})
    fields = ['case_id', 'stage', 'generation_status', 'quality_status', 'pareto', 'failure_reason',
              *params, *metrics, 'process_elapsed_s', 'attempt_dir']
    rows = []
    for r in results:
        q, reasons = quality(r, cfg)
        row = {k: r.get(k, '') for k in fields}
        row.update(r.get('parameters_m', {}))
        row.update(r.get('metrics', {}))
        row.update(quality_status=q, pareto=r['case_id'] in front,
                   failure_reason=r.get('failure_reason') or '; '.join(reasons))
        rows.append(row)
    with (output / 'summary.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    atomic_json(output / 'results.json', {'evidence_kind': 'measured_only', 'results': results,
                                        'pareto_case_ids': sorted(front)})
    template = Path(__file__).with_name('dashboard.html').read_text(encoding='utf-8')
    payload = json.dumps({'rows': rows, 'parameters': params, 'metrics': metrics}, allow_nan=False)
    payload = payload.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    (output / 'dashboard.html').write_text(template.replace('/*__DATA__*/null', payload), encoding='utf-8')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='config/campaign.json')
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('check')
    d = sub.add_parser('design')
    d.add_argument('--stage', choices=['pilot', 'doe'], default='pilot')
    d.add_argument('--count', type=int, default=3)
    d.add_argument('--seed', type=int, default=20261028)
    d.add_argument('--output', required=True)
    r = sub.add_parser('run')
    r.add_argument('--cases', required=True)
    r.add_argument('--out', required=True)
    r.add_argument('--limit', type=int, default=3)
    r.add_argument('--retry', action='store_true')
    s = sub.add_parser('summarize')
    s.add_argument('--runs', default='runs')
    s.add_argument('--out', default='results')
    args = parser.parse_args()
    try:
        cfg = read_json(args.config)
        if args.action == 'check':
            validate_config(cfg, execution=True)
            print('Configuration and evidence files verified; this is not a STAR runtime test.')
        elif args.action == 'design':
            design(cfg, args.output, args.stage, args.count, args.seed)
        elif args.action == 'run':
            run(cfg, args.cases, args.out, args.limit, args.retry)
        else:
            print(f'{len(summarize(cfg, args.runs, args.out))} recorded cases summarized')
    except (ConfigurationError, OSError, ValueError, KeyError) as exc:
        print(f'BLOCKED: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
