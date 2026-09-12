"""Disk-backed construction of EVERY row in the official full segment graph.
No status, NT, ROI, confidence or weight filtering beyond the published file.
"""
import hashlib,json,time
from pathlib import Path
import numpy as np
import pyarrow as pa

ROOT=Path(__file__).resolve().parent
RAW=ROOT/'data/raw/connectome-weights-male-cns-v1.0-minconf-0.5.feather'
OUT=ROOT/'data/graph_full';OUT.mkdir(parents=True,exist_ok=True)
source=pa.memory_map(str(RAW),'r');reader=pa.ipc.open_file(source)
start=time.perf_counter()
receipt=json.loads(RAW.with_suffix('.feather.receipt.json').read_text())
assert hashlib.sha256(RAW.read_bytes()).hexdigest()==receipt['sha256']
assert receipt['sha256']=='e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1'
total=sum(reader.get_batch(i).num_rows for i in range(reader.num_record_batches))
idsfile=OUT/'endpoint_sort.npy'
if not (OUT/'body_ids.npy').exists():
    all_ids=np.lib.format.open_memmap(idsfile,mode='w+',dtype=np.uint32,shape=(total*2,))
    at=0
    for i in range(reader.num_record_batches):
        b=reader.get_batch(i)
        for j in [0,1]:
            a=b.column(j).to_numpy();assert a.min()>=0 and a.max()<2**32
            all_ids[at:at+len(a)]=a;at+=len(a)
    all_ids.flush();print('sorting endpoints',total*2,flush=True)
    all_ids.sort(kind='quicksort');all_ids.flush()
    parts=[];last=-1
    for lo in range(0,len(all_ids),1000000):
        unique=np.unique(all_ids[lo:lo+1000000]);unique=unique[unique!=last]
        if len(unique):last=int(unique[-1]);parts.append(unique)
    ids=np.concatenate(parts);np.save(OUT/'body_ids.npy',ids)
    del parts,all_ids
ids=np.load(OUT/'body_ids.npy',mmap_mode='r');n=len(ids)
print('full graph nodes',n,'edges',total,flush=True)
# Exact O(1) uint32 ID rank lookup: presence bitmap + prefix popcounts.
# Avoid billions of cache-missing binary-search comparisons in this 88M-ID graph.
words=(int(ids[-1])>>6)+1
if not (OUT/'id_rank.npy').exists():
    bits=np.lib.format.open_memmap(OUT/'id_bits.npy',mode='w+',dtype=np.uint64,shape=(words,));bits[:]=0
    for lo in range(0,n,1000000):
        v=ids[lo:lo+1000000].astype(np.uint64)
        np.bitwise_or.at(bits,v>>6,np.left_shift(np.uint64(1),v&63))
    bits.flush()
    rank=np.lib.format.open_memmap(OUT/'id_rank.npy',mode='w+',dtype=np.uint32,shape=(words+1,));rank[0]=0
    np.cumsum(np.bitwise_count(bits),dtype=np.uint32,out=rank[1:]);rank.flush()
    assert int(rank[-1])==n
bits=np.load(OUT/'id_bits.npy',mmap_mode='r');rank=np.load(OUT/'id_rank.npy',mmap_mode='r')
def lookup(values):
    v=values.astype(np.uint64,copy=False);word=v>>6;mask=np.left_shift(np.uint64(1),v&63)-np.uint64(1)
    result=(rank[word]+np.bitwise_count(bits[word]&mask)).astype(np.int32)
    if not np.array_equal(ids[result],values):raise ValueError('Endpoint lookup does not match source IDs')
    return result
assert np.array_equal(lookup(ids[::10000]),np.arange(0,n,10000))
if not (OUT/'indptr.npy').exists():
    degree=np.zeros(n,np.int64);synapses=0
    for i in range(reader.num_record_batches):
        b=reader.get_batch(i);post=b.column(1).to_numpy();w=b.column(2).to_numpy()
        assert (w>0).all() and w.max()<2**32
        rows=lookup(post);unique,counts=np.unique(rows,return_counts=True);degree[unique]+=counts;synapses+=int(w.sum())
        if i%500==0:print('count',i,'/',reader.num_record_batches,flush=True)
    indptr=np.r_[0,np.cumsum(degree)];assert indptr[-1]==total
    np.save(OUT/'indptr.npy',indptr.astype(np.int32))
    (OUT/'count_pass.json').write_text(json.dumps({'synapses':synapses,'rows':total}))
indptr=np.load(OUT/'indptr.npy');cursor=indptr[:-1].astype(np.int64)
indices=np.lib.format.open_memmap(OUT/'indices.npy',mode='w+',dtype=np.int32,shape=(total,))
counts=np.lib.format.open_memmap(OUT/'counts.npy',mode='w+',dtype=np.uint32,shape=(total,))
for i in range(reader.num_record_batches):
    b=reader.get_batch(i);pre,post,w=[b.column(j).to_numpy() for j in range(3)]
    rows=lookup(post);cols=lookup(pre)
    order=np.argsort(rows,kind='stable');rows,cols,w=rows[order],cols[order],w[order]
    starts=np.r_[0,np.flatnonzero(np.diff(rows))+1];sizes=np.diff(np.r_[starts,len(rows)])
    positions=cursor[rows]+np.arange(len(rows))-np.repeat(starts,sizes)
    indices[positions]=cols;counts[positions]=w;cursor[rows[starts]]+=sizes
    if i%500==0:print('fill',i,'/',reader.num_record_batches,flush=True)
assert np.array_equal(cursor,indptr[1:]);indices.flush();counts.flush()
from scipy.sparse import csr_matrix
c=csr_matrix((counts,indices,indptr),shape=(n,n),copy=False);c.sort_indices()
assert c.has_canonical_format,'Duplicate edges must be investigated, never silently summed'
expected=json.loads((OUT/'count_pass.json').read_text())
assert int(c.sum(dtype=np.uint64))==expected['synapses']
indices.flush();counts.flush()
audit={'scope':'ALL rows and endpoints of official full segment graph','nodes':n,'edges':total,'excluded_rows':0,
       'source_sha256':receipt['sha256'],'synapse_count_sum':expected['synapses'],'orientation':'C[post,pre]',
       'duplicates_checked':True,'weight_threshold_applied':False,'seconds':time.perf_counter()-start,
       'warning':'Segments include fragments and unannotated bodies; counts are structural, not physiological weights.',
       'files':{f:hashlib.sha256((OUT/f).read_bytes()).hexdigest() for f in ['body_ids.npy','indptr.npy','indices.npy','counts.npy']}}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit),flush=True)
