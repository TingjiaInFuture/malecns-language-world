"""Reproducible software evidence, kept separate from biological acceptance."""
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    result = {'scope':'software and local structural audit only','biological_acceptance':False,
        'python':sys.version,'platform':platform.platform(),'commands':[]}
    for args in [[sys.executable,'-m','unittest','discover','-s','habitat3d','-p','test_*.py','-v'],
                 [sys.executable,'-m','unittest','discover','-s','validation','-p','test_*.py','-v'],
                 ['node','--check','habitat3d/ui/scene.js']]:
        start = time.perf_counter()
        run = subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
        result['commands'].append({'argv':args,'returncode':run.returncode,
            'seconds':time.perf_counter()-start,'stdout':run.stdout,'stderr':run.stderr})
        print(run.stdout+run.stderr,flush=True)
    graph = ROOT/'data/graph_neurons/audit.json'
    result['graph'] = json.loads(graph.read_text()) if graph.exists() else {'status':'MISSING'}
    for name, path in [('body','validation/body-evidence.json'),
                       ('source_samples','data/graph_neurons/source_sample_audit.json'),
                       ('closed_loop','validation/closed-loop-evidence.json'),
                       ('full_neuron_benchmark','validation/full-neuron-evidence.json'),
                       ('interface_research','validation/interface-research.json'),
                       ('public_data','validation/public-data-availability.json'),
                       ('manc_crosswalk','validation/manc-crosswalk-evidence.json')]:
        p = ROOT/path
        result[name] = json.loads(p.read_text()) if p.exists() else {'status':'MISSING'}
    result['source_hashes'] = {}
    for directory in ['connectome','physiology','interfaces','world','experiments','body','validation','habitat3d']:
        for p in (ROOT/directory).glob('*.py'):
            result['source_hashes'][str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    for relative in ['habitat3d/ui/scene.js','habitat3d/start.ps1','requirements-body.lock.txt']:
        result['source_hashes'][relative] = hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()
    result['software_pass'] = all(c['returncode']==0 for c in result['commands'])
    (ROOT/'validation/realism-evidence.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    return 0 if result['software_pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
