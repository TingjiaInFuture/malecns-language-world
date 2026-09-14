"""Retrieve public experimental metadata and selected assets with verifiable receipts.

Failed HTTP requests remain failures, with local_path=null. No credential lookup,
synthetic substitution, or automatic download of the 48 GB motor dataset.

Dryad policy (verified 2026-09-14): anonymous API users cannot download file
bytes; a free self-service API account is required. Set DRYAD_API_TOKEN to a
current bearer token (profile -> "Create a Dryad API account"; refresh via
POST https://datadryad.org/oauth/token with client_id/client_secret,
grant_type=client_credentials; tokens last 10 hours). The token is used only
as a request header and is never written to receipts or reports.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import urllib.request
from urllib.parse import quote

ROOT=Path('data/physiology_raw')
DRYAD='https://datadryad.org'


def dryad_auth_headers():
    token=os.environ.get('DRYAD_API_TOKEN','').strip()
    return {'Authorization':'Bearer '+token} if token else None


class _AuthlessRedirect(urllib.request.HTTPRedirectHandler):
    """Strip the bearer header when Dryad redirects to its asset store.

    The presigned asset URL rejects requests carrying an Authorization header,
    and forwarding the token to a third-party host would leak it.
    """
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        request = super().redirect_request(req, fp, code, msg, headers, newurl)
        if request is not None:
            for store in (request.headers, request.unredirected_hdrs):
                store.pop('Authorization', None)
        return request


def get_json(url):
    with urllib.request.urlopen(url,timeout=45) as response:
        return json.load(response)


def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def retrieve(url,path,expected_sha=None,expected_size=None,headers=None):
    record={'url':url,'local_path':None,'status':'not_downloaded','retrieved_at':datetime.now(timezone.utc).isoformat()}
    if headers and 'Authorization' in headers:
        record['token_authenticated']=True
    partial=path.with_suffix(path.suffix+'.part')
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():
            receipt=path.with_suffix(path.suffix+'.receipt.json')
            previous=json.loads(receipt.read_text()) if receipt.exists() else {}
            expected=expected_sha or previous.get('sha256')
            if expected is None or sha256(path)!=expected:raise ValueError('Unverified existing file '+str(path))
            if expected_size is not None and path.stat().st_size!=expected_size:raise ValueError('Byte count mismatch')
            if previous.get('url',url)!=url:raise ValueError('Existing receipt belongs to another source')
        else:
            request=urllib.request.Request(url,headers=headers or {})
            if headers and 'Authorization' in headers:
                opener=urllib.request.build_opener(_AuthlessRedirect())
                response=opener.open(request,timeout=45)
            else:
                response=urllib.request.urlopen(request,timeout=45)
            with response,partial.open('wb') as stream:
                for block in iter(lambda:response.read(1024*1024),b''):stream.write(block)
            if expected_size is not None and partial.stat().st_size!=expected_size:raise ValueError('Byte count mismatch')
            if expected_sha is not None and sha256(partial)!=expected_sha:raise ValueError('Publisher SHA-256 mismatch')
            if path.suffix=='.parquet':
                with partial.open('rb') as stream:
                    if stream.read(4)!=b'PAR1':raise ValueError('Not Parquet')
                    stream.seek(-4,2)
                    if stream.read(4)!=b'PAR1':raise ValueError('Truncated Parquet')
            partial.replace(path)
        record.update(status='downloaded_verified',local_path=str(path.resolve()),sha256=sha256(path),bytes=path.stat().st_size,
            publisher_sha256_verified=expected_sha is not None)
        path.with_suffix(path.suffix+'.receipt.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    except Exception as error:
        record.update(status='download_failed',error=type(error).__name__+': '+str(error))
    return record


def dryad_catalog(doi):
    dataset=get_json(DRYAD+'/api/v2/datasets/'+quote('doi:'+doi,safe=''))
    version=get_json(DRYAD+dataset['_links']['stash:version']['href'])
    url=DRYAD+version['_links']['stash:files']['href']
    files=[]
    while url:
        page=get_json(url);files.extend(page['_embedded']['stash:files'])
        next_page=page['_links'].get('next',{}).get('href')
        url=DRYAD+next_page if next_page else None
    return {'doi':doi,'version':version,'files':files}


def paper_quality_tables():
    """Per-ROI synapse quality CSVs from the MaleCNS paper repository (no token)."""
    base = 'https://raw.githubusercontent.com/flyconnectome/2025malecns/main/supplemental_data/'
    names = ['male-cns-v1.0-traced-synapse-capture-by-roi.csv',
             'male-cns-v1.0-synapse-connection-precision-recall-by-roi.csv',
             'male-cns-v1.0-synapse-tbar-precision-recall-by-roi.csv']
    records = []
    for name in names:
        record = retrieve(base+name, Path('data/raw/quality')/name)
        record.update(dataset='flyconnectome/2025malecns supplemental_data')
        records.append(record)
        print(name, record['status'], flush=True)
    return records


def dallmann_supplement():
    """Dallmann 2025 Supplementary Table 2 (open Springer URL, no token)."""
    url = ('https://media.springernature.com/original/springer-static/esm/'
           'art%3A10.1038%2Fs41586-025-09554-2/MediaObjects/41586_2025_9554_MOESM4_ESM.xlsx')
    target = ROOT/'feco-author/dallmann2025_supp_table2.xlsx'
    record = retrieve(url, target)
    record.update(dataset='Dallmann et al. 2025 Nature 647:445-453, Supplementary Table 2')
    print(target.name, record['status'], flush=True)
    return [record]


def motor_selected_assets(names=('MN_anatomy_confocal_measurements.xlsx',)):
    """Token-gated Dryad motor files by catalog name; single-stream and idempotent.

    The Merritt asset host has shown ~12 KB/s per-connection throttling; large
    zips may take hours. Existing publisher-verified receipts short-circuit.
    """
    catalog = json.loads((ROOT/'motor-catalog.json').read_text(encoding='utf-8'))
    available = {f['path']: f for f in catalog['files']}
    unknown = [name for name in names if name not in available]
    if unknown:
        raise ValueError('Unknown motor catalog file(s): '+','.join(unknown))
    headers = dryad_auth_headers()
    if not headers:
        raise RuntimeError('DRYAD_API_TOKEN required for motor assets')
    records = []
    for name in names:
        entry = available.get(name)
        record = retrieve(DRYAD+entry['_links']['stash:download']['href'], ROOT/'motor'/name,
                          entry['digest'] if entry['digestType'] == 'sha-256' else None,
                          entry['size'], headers=headers)
        record.update(dataset='10.5061/dryad.76hdr7stb (Azevedo et al. 2020)')
        records.append(record)
        print(name, record['status'], flush=True)
    return records


def motor_author_assets():
    """Official related Zenodo record: analysis code, not raw trial archives."""
    catalog=get_json('https://zenodo.org/api/records/4527659')
    (ROOT/'motor-zenodo-4527659.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
    selected={'README.txt','Methods_ForceProbeCalibration.m','Dataset3_SlowInterFast_ForcePerSpike.m'}
    records=[]
    for file in catalog['files']:
        if file['key'] not in selected:continue
        path=ROOT/'motor-author'/file['key']
        record=retrieve(file['links']['self'],path,expected_size=file['size'])
        record.update(dataset='Zenodo 4527659; motor analysis code only',publisher_checksum=file['checksum'])
        if record['status']=='downloaded_verified':
            digest=hashlib.md5(path.read_bytes()).hexdigest()
            record['publisher_md5_verified']=file['checksum']=='md5:'+digest
            if not record['publisher_md5_verified']:
                record.update(status='download_failed',local_path=None,error='Publisher MD5 mismatch')
            path.with_suffix(path.suffix+'.receipt.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        records.append(record)
    return records


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    report={'created_at':datetime.now(timezone.utc).isoformat(),'biological_acceptance':False,'datasets':[],'assets':[]}
    for key,doi in [('feco','10.5061/dryad.gqnk98t16'),('motor','10.5061/dryad.76hdr7stb')]:
        try:
            catalog=dryad_catalog(doi)
            (ROOT/(key+'-catalog.json')).write_text(json.dumps(catalog,indent=2),encoding='utf-8')
            report['datasets'].append({'key':key,'doi':doi,'files':len(catalog['files']),
                'version':catalog['version']['versionNumber'],'status':'metadata_retrieved'})
            selected={'README.md','hook_flexion_01_magnet.parquet','manc_v1_classifications.csv',
                      'manc_v1_connectivity.parquet','fanc_dn_information.csv','rna-seq.xlsx'} if key=='feco' else {'README.txt'}
            for file in catalog['files']:
                if file['path'] not in selected:continue
                record=retrieve(DRYAD+file['_links']['stash:download']['href'],ROOT/key/file['path'],
                    file['digest'] if file['digestType']=='sha-256' else None,file['size'],
                    headers=dryad_auth_headers())
                report['assets'].append(dict(record,dataset=doi,publisher_metadata=file))
                print(key,file['path'],record['status'],flush=True)
        except Exception as error:
            report['datasets'].append({'key':key,'doi':doi,'status':'metadata_failed','error':str(error)})
    article=get_json('https://api.elifesciences.org/articles/96084')
    (ROOT/'elife-96084-metadata.json').write_text(json.dumps(article,indent=2),encoding='utf-8')
    for file in article['additionalFiles']:
        if file['id'] in ['supp3','supp6']:
            record=retrieve(file['uri'],ROOT/'manc'/file['filename'])
            report['assets'].append(dict(record,title=file.get('title'),dataset='MANC; eLife 96084 supplement'))
            print(file['filename'],record['status'],flush=True)
    try:report['assets'].extend(paper_quality_tables())
    except Exception as error:report['datasets'].append({'key':'paper_quality','status':'failed','error':str(error)})
    try:report['assets'].extend(dallmann_supplement())
    except Exception as error:report['datasets'].append({'key':'dallmann_supplement','status':'failed','error':str(error)})
    try:
        motor_names=['MN_anatomy_confocal_measurements.xlsx']
        if (ROOT/'motor/180222_F1_C1.zip').exists() or dryad_auth_headers():
            motor_names.append('180222_F1_C1.zip')
        report['assets'].extend(motor_selected_assets(tuple(motor_names)))
    except Exception as error:report['datasets'].append({'key':'motor_selected','status':'failed','error':str(error)})
    for name in ['data/README.md','code/utils/imaging_predict_gcamp.m','code/imaging_config.toml']:
        url='https://raw.githubusercontent.com/chrisjdallmann/feco-inhibition/main/'+name
        record=retrieve(url,ROOT/'feco-author'/name)
        report['assets'].append(dict(record,dataset='feco-inhibition author repository'))
    try:report['assets'].extend(motor_author_assets())
    except Exception as error:
        report['datasets'].append({'key':'motor_author','status':'metadata_failed','error':str(error)})
    Path('validation/public-data-availability.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':main()
