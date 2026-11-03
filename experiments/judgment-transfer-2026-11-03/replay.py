"""Replay disclosed saved choices in fresh temporary directories; no AI/native.

This is a public saved-work replay, not a rerun of the original research trial.
SQLite binary hashes and timestamped engine result hashes are not compared.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import types


def bootstrap_package(folder):
    """Check every package byte before executing any other package module.

    replay.py and the downloaded publisher are the trust boundary. A consistent
    manifest is an integrity check, not a signature or a sandbox for untrusted
    Python. The schema verifier is loaded only after its manifest hash matches.
    """
    def need(condition, message):
        if not condition:
            raise ValueError(message)
    def unique(pairs):
        value = {}
        for key, item in pairs:
            need(key not in value, 'Duplicate package JSON key')
            value[key] = item
        return value
    def nonfinite(_):
        raise ValueError('Nonfinite package JSON number')
    def loads(raw):
        return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)
    folder = Path(folder)
    need(not folder.is_symlink() and folder.is_dir(), 'Regular saved-work package required')
    manifest_path = folder / 'MANIFEST.json'
    need(not manifest_path.is_symlink() and manifest_path.is_file(), 'Regular replay manifest required')
    manifest = loads(manifest_path.read_bytes())
    names = {'evidence.json', 'verify.py', 'README.md', 'worlds.json', 'plans.json', 'common.py', 'world_engine.py', 'replay.py'}
    need(type(manifest) is dict and set(manifest) == {'schema', 'replay', 'files'} and manifest['schema'] == 'judgment-transfer-public-package.v1' and manifest['replay'] is True, 'Saved-work manifest schema differs')
    need(type(manifest['files']) is dict and set(manifest['files']) == names, 'Saved-work manifest inventory differs')
    need({p.name for p in folder.iterdir()} == names | {'MANIFEST.json'}, 'Unexpected saved-work package file')
    content = {}
    for name in sorted(names):
        path, record = folder / name, manifest['files'][name]
        need(not path.is_symlink() and path.is_file(), 'Regular saved-work files required')
        need(type(record) is dict and set(record) == {'bytes', 'sha256'} and type(record['bytes']) is int and record['bytes'] >= 0 and type(record['sha256']) is str, 'Saved-work file record differs')
        raw = path.read_bytes()
        need(len(raw) == record['bytes'] and sha256(raw).hexdigest() == record['sha256'], 'Saved-work package file hash mismatch: ' + name)
        content[name] = raw
    evidence = loads(content['evidence.json'])
    need(type(evidence) is dict and type(evidence.get('hashes')) is dict, 'Saved evidence code pins required')
    for name, pin in [('common.py', 'common_py_sha256'), ('world_engine.py', 'world_engine_py_sha256')]:
        need(sha256(content[name]).hexdigest() == evidence['hashes'].get(pin), 'Saved-work own-engine digest mismatch: ' + name)
    return content


def load_verified_module(name, raw, folder):
    """Execute the captured, already-checked bytes, not a newly resolved path."""
    module = types.ModuleType(name)
    module.__file__ = str(folder / (name + '.py'))
    sys.modules[name] = module
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', nargs='?', type=Path, default=Path(__file__).with_name('evidence.json'))
    args = parser.parse_args(argv)
    folder = args.evidence.parent
    if args.evidence.name != 'evidence.json':
        raise ValueError('Replay requires the package-local evidence.json')
    content = bootstrap_package(folder)
    verify = load_verified_module('verify', content['verify.py'], folder)
    data = verify.validate_summary(verify.parse_json(content['evidence.json']))
    verify.verify_bundle(folder)
    # Only after the entire package and strict evidence validation succeeds do
    # these pinned captured engine bytes execute. External/preloaded names lose.
    load_verified_module('common', content['common.py'], folder)
    world_engine = load_verified_module('world_engine', content['world_engine.py'], folder)
    worlds = {w['world_id']: w for w in data['worlds']}
    compared, unavailable, abstentions = 0, 0, 0
    with tempfile.TemporaryDirectory(prefix='judgment-transfer-public-replay-') as temporary:
        # macOS exposes its temp directory through /var -> /private/var. The
        # unchanged engine rejects aliased paths, so pass the canonical fresh
        # directory rather than weakening that gate or touching original work.
        replay_root = Path(temporary).resolve(strict=True)
        for row in data['rows']:
            if row['final']['decision'] == 'abstain':
                abstentions += 1
                continue
            world = worlds[row['world_id']]
            result = world_engine.execute(world, world['probes'][row['phase']], row['final']['operation'], replay_root / row['assignment_id'])
            expected = row['target_validation']
            if expected is None:
                unavailable += 1
                continue
            verify.need(result['status'] == row['operation_status'], 'Saved operation status differs: ' + row['assignment_id'])
            for field in ('accepted', 'state_valid', 'process_completed', 'validation_basis', 'artifact_sha256'):
                verify.need(result['validation'][field] == expected[field], 'Saved semantic/artifact result differs: ' + row['assignment_id'] + ' / ' + field)
            compared += 1
    print('Public saved-work replay: compared', compared, 'saved target operations;', abstentions, 'saved abstentions;', unavailable, 'original target evaluations unavailable.')
    print('No original trial, native LRE, fresh AI choices, timestamped result hashes or SQLite binary hashes were replayed.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, UnicodeError) as error:
        raise SystemExit(str(error)) from error
