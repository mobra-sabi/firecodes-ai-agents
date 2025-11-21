#!/usr/bin/env python3
"""
🚀 PROCESARE PARALELĂ AGENȚI CU MULTIPLE GPU-uri
================================================

Procesează agenții în paralel folosind:
- vLLM pe portul 9301 pentru LLM inference
- GPU 6-10 pentru embeddings (1 agent per GPU)
- MongoDB și Qdrant pentru storage

USAGE:
    python3 parallel_agent_processor.py
"""

import torch
import multiprocessing as mp
from pymongo import MongoClient
from bson import ObjectId
import sys
import os
import time
from datetime import datetime
sys.path.insert(0, '/srv/hf/ai_agents')

# Import modulele necesare
from tools.construction_agent_creator import ConstructionAgentCreator
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

def process_agent_on_gpu(gpu_id: int, agent_data: dict, results_queue: mp.Queue):
    """
    Procesează un agent pe un GPU specific
    
    Args:
        gpu_id: ID-ul GPU-ului (6-10)
        agent_data: Dict cu agent_id, domain, site_url
        results_queue: Queue pentru rezultate
    """
    try:
        # Set GPU
        os.environ['CUDA_VISIBLE_DEVICES'] = str(gpu_id)
        device = f"cuda:0"  # După setare, devine primul GPU disponibil
        
        agent_id = agent_data['agent_id']
        domain = agent_data['domain']
        site_url = agent_data['site_url']
        
        print(f"\n{'='*70}")
        print(f"🎮 GPU {gpu_id} | Agent: {domain}")
        print(f"{'='*70}")
        print(f"   Agent ID: {agent_id}")
        print(f"   URL: {site_url}")
        print(f"   Start: {datetime.now().strftime('%H:%M:%S')}")
        
        # STEP 1: Creează agent cu construction_agent_creator
        # (folosește vLLM 9301 pentru LLM calls)
        print(f"\n[GPU {gpu_id}] STEP 1/3: Creare agent cu construction_agent_creator...")
        creator = ConstructionAgentCreator()
        creator.create_site_agent(site_url)
        
        # STEP 2: Extrage conținut din MongoDB
        print(f"\n[GPU {gpu_id}] STEP 2/3: Extragere conținut din MongoDB...")
        mongo = MongoClient("mongodb://localhost:27017/")
        db = mongo.ai_agents_db
        
        # Găsește agentul creat
        agent = db.site_agents.find_one({'domain': domain}, sort=[("created_at", -1)])
        if not agent:
            raise Exception(f"Agent {domain} nu găsit în MongoDB")
        
        agent_id_obj = agent['_id']
        contents = list(db.site_content.find({"agent_id": agent_id_obj}))
        
        if not contents:
            print(f"[GPU {gpu_id}] ⚠️  Nu există conținut pentru procesare")
            results_queue.put({
                'success': False,
                'gpu_id': gpu_id,
                'domain': domain,
                'error': 'No content found'
            })
            return
        
        print(f"[GPU {gpu_id}]    Găsite {len(contents)} chunks de conținut")
        
        # STEP 3: Generează embeddings pe GPU
        print(f"\n[GPU {gpu_id}] STEP 3/3: Generare embeddings pe GPU {gpu_id}...")
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device=device)
        
        texts = [c['content'] for c in contents if c.get('content')]
        
        start_time = time.time()
        embeddings = model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        elapsed = time.time() - start_time
        
        print(f"[GPU {gpu_id}]    ✅ {len(embeddings)} embeddings în {elapsed:.1f}s ({len(texts)/elapsed:.1f} txt/s)")
        
        # STEP 4: Upload la Qdrant
        print(f"\n[GPU {gpu_id}] STEP 4/4: Upload către Qdrant...")
        qdrant = QdrantClient(url="http://localhost:9306")
        collection_name = f"agent_{agent_id_obj}_content"
        
        # Recreate collection
        try:
            qdrant.delete_collection(collection_name=collection_name)
        except:
            pass
        
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        
        # Upload points
        points = []
        for idx, (content, embedding) in enumerate(zip(contents, embeddings)):
            points.append(PointStruct(
                id=idx,
                vector=embedding.tolist(),
                payload={
                    "text": content['content'][:1000],
                    "url": content.get('url', ''),
                    "agent_id": str(agent_id_obj),
                    "chunk_index": idx
                }
            ))
        
        qdrant.upsert(collection_name=collection_name, points=points)
        
        # Update agent în MongoDB
        db.site_agents.update_one(
            {"_id": agent_id_obj},
            {"$set": {
                "chunks_indexed": len(points),
                "pages_indexed": len(set(c.get('url', '') for c in contents)),
                "has_embeddings": True,
                "status": "active",
                "last_processed": datetime.now()
            }}
        )
        
        print(f"\n[GPU {gpu_id}] ✅ SUCCES: {domain}")
        print(f"[GPU {gpu_id}]    Chunks: {len(points)}")
        print(f"[GPU {gpu_id}]    Timp total: {time.time() - start_time:.1f}s")
        
        results_queue.put({
            'success': True,
            'gpu_id': gpu_id,
            'domain': domain,
            'chunks': len(points),
            'pages': len(set(c.get('url', '') for c in contents))
        })
        
    except Exception as e:
        print(f"\n[GPU {gpu_id}] ❌ EROARE: {domain}")
        print(f"[GPU {gpu_id}]    {str(e)}")
        import traceback
        traceback.print_exc()
        
        results_queue.put({
            'success': False,
            'gpu_id': gpu_id,
            'domain': domain,
            'error': str(e)
        })


def get_agents_to_process(limit=5):
    """Obține agenții care au nevoie de procesare"""
    mongo = MongoClient("mongodb://localhost:27017/")
    db = mongo.ai_agents_db
    
    # Găsește agenții fără date complete
    agents = list(db.site_agents.find({
        '$or': [
            {'chunks_indexed': {'$exists': False}},
            {'chunks_indexed': 0},
            {'pages_indexed': 0}
        ]
    }).limit(limit))
    
    return [{
        'agent_id': str(agent['_id']),
        'domain': agent.get('domain', 'N/A'),
        'site_url': agent.get('site_url', f"https://{agent.get('domain', '')}")
    } for agent in agents]


def main():
    """Main function pentru procesare paralelă"""
    
    print("\n" + "="*80)
    print("🚀 PROCESARE PARALELĂ AGENȚI - MULTI-GPU")
    print("="*80)
    print(f"⏰ Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verifică GPU-uri disponibile
    if not torch.cuda.is_available():
        print("❌ CUDA nu este disponibil!")
        return
    
    total_gpus = torch.cuda.device_count()
    print(f"\n🎮 GPU-uri detectate: {total_gpus}")
    
    # Folosim GPU 6-10 (5 GPU-uri pentru procesare paralelă)
    worker_gpus = list(range(6, min(11, total_gpus)))
    print(f"   GPU-uri pentru procesare: {worker_gpus}")
    
    if not worker_gpus:
        print("❌ Nu există GPU-uri libere pentru procesare!")
        return
    
    # Obține agenți de procesare
    agents_to_process = get_agents_to_process(limit=len(worker_gpus))
    
    if not agents_to_process:
        print("\n✅ Nu există agenți de procesare!")
        return
    
    print(f"\n📊 Agenți de procesat: {len(agents_to_process)}")
    for i, agent in enumerate(agents_to_process, 1):
        print(f"   {i}. {agent['domain']}")
    
    # Procesare paralelă
    print(f"\n{'='*80}")
    print(f"🚀 PORNESC PROCESARE PARALELĂ PE {len(worker_gpus)} GPU-uri")
    print(f"{'='*80}\n")
    
    results_queue = mp.Queue()
    processes = []
    
    start_time = time.time()
    
    # Pornește câte un proces per GPU
    for gpu_id, agent_data in zip(worker_gpus, agents_to_process):
        p = mp.Process(
            target=process_agent_on_gpu,
            args=(gpu_id, agent_data, results_queue)
        )
        p.start()
        processes.append(p)
        time.sleep(2)  # Stagger start
    
    # Așteaptă finalizarea
    for p in processes:
        p.join()
    
    # Colectează rezultate
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())
    
    elapsed = time.time() - start_time
    
    # Raport final
    print(f"\n{'='*80}")
    print(f"📊 RAPORT FINAL PROCESARE PARALELĂ")
    print(f"{'='*80}")
    print(f"\n⏱️  Timp total: {elapsed/60:.1f} minute")
    print(f"📊 Rezultate:")
    
    success_count = sum(1 for r in results if r['success'])
    failed_count = len(results) - success_count
    
    print(f"   ✅ Succese: {success_count}")
    print(f"   ❌ Eșuări: {failed_count}")
    
    print(f"\n📝 Detalii:")
    for result in sorted(results, key=lambda x: x['gpu_id']):
        gpu_id = result['gpu_id']
        domain = result['domain']
        if result['success']:
            chunks = result['chunks']
            pages = result['pages']
            print(f"   ✅ GPU {gpu_id} | {domain}: {chunks} chunks, {pages} pages")
        else:
            error = result.get('error', 'Unknown')
            print(f"   ❌ GPU {gpu_id} | {domain}: {error}")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    # Necesară pentru multiprocessing pe Linux
    mp.set_start_method('spawn', force=True)
    main()

