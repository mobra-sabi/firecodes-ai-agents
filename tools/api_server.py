import re
#!/usr/bin/env python3
import os, sys, json
from langchain_ollama import OllamaEmbeddings
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
import threading
import time

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL","nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL","http://127.0.0.1:11434")
def get_embedder():
    return OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)


# Import pipeline-ul principal
sys.path.append('/home/mobra/ai_agents/tools')
from intelligent_pipeline import UltraOptimizedPipeline

def create_api_server():
    app = Flask(__name__)
    pipeline = UltraOptimizedPipeline()
    
    @app.route('/api/analyze', methods=['POST'])
    def analyze_site():
        data = request.json
        site_url = data.get('url')
        question = data.get('question', 'Ce oferă această companie?')
        
        if not site_url:
            return jsonify({"error": "URL lipsește"}), 400
        
        try:
            plan = pipeline.create_plan_with_gpt4(site_url)
            personality = plan.get('chat_personality', 'expert în business')
            answer = pipeline.chat_with_semantic_context(question, site_url, personality)
            
            return jsonify({
                "success": True,
                "url": site_url,
                "plan": plan,
                "answer": answer,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/search', methods=['POST'])
    def semantic_search():
        data = request.json
        query = data.get('query')
        domain = data.get('domain')
        limit = data.get('limit', 10)
        
        if not query:
            return jsonify({"error": "Query lipsește"}), 400
        
        results = pipeline.semantic_search_qdrant(query, domain, limit)
        return jsonify({"results": results})
    
    @app.route('/api/status', methods=['GET'])
    def status():
        active_endpoints = [ep for ep in pipeline.llm_endpoints if ep.active]
        total_docs = pipeline.collection.count_documents({})
        
        try:
            qdrant_info = pipeline.qdrant.get_collection("website_embeddings")
            total_embeddings = getattr(qdrant_info, "points_count", getattr(qdrant_info, "vectors_count", 0))
        except:
            total_embeddings = 0
        
        return jsonify({
            "active_endpoints": len(active_endpoints),
            "total_endpoints": len(pipeline.llm_endpoints),
            "mongodb_documents": total_docs,
            "qdrant_embeddings": total_embeddings,
            "cache_size": len(pipeline.response_cache)
        })
    
    @app.route('/api/benchmark', methods=['POST'])
    def benchmark():
        try:
            pipeline.benchmark_all_endpoints()
            return jsonify({"success": True, "message": "Benchmark completat"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/generate_embeddings', methods=['POST'])
    def generate_embeddings():
        try:
            # Rulează în background
            def run_embeddings():
                pipeline.auto_generate_embeddings()
            
            thread = threading.Thread(target=run_embeddings)
            thread.daemon = True
            thread.start()
            
            return jsonify({"success": True, "message": "Generarea embeddings pornită în background"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/dashboard')
    def dashboard():
        return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>🚀 AI Pipeline Dashboard Ultra</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .card { background: white; border: 1px solid #ddd; padding: 20px; margin: 10px 0; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status { color: green; font-weight: bold; font-size: 18px; }
        input, button { padding: 12px; margin: 5px; border: 1px solid #ddd; border-radius: 5px; }
        button { background: #007bff; color: white; cursor: pointer; }
        button:hover { background: #0056b3; }
        .result { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 10px; max-height: 400px; overflow-y: auto; }
        .loading { color: #666; font-style: italic; }
        .error { color: red; }
        .success { color: green; }
        pre { background: #f8f9fa; padding: 10px; border-radius: 5px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>🚀 AI Pipeline Dashboard Ultra</h1>
    
    <div class="card">
        <h2>📊 Status Sistem</h2>
        <div id="status">Loading...</div>
        <button onclick="loadStatus()">🔄 Refresh Status</button>
        <button onclick="runBenchmark()">🏁 Benchmark</button>
        <button onclick="generateEmbeddings()">🧠 Generează Embeddings</button>
    </div>
    
    <div class="card">
        <h2>🔍 Analiză Site Completă</h2>
        <input type="url" id="siteUrl" placeholder="https://example.com" style="width: 300px;">
        <input type="text" id="question" placeholder="Ce produse oferă?" style="width: 300px;">
        <button onclick="analyzeSite()">🚀 Analizează</button>
        <div id="analysisResult"></div>
    </div>
    
    <div class="card">
        <h2>🔍 Căutare Semantică</h2>
        <input type="text" id="searchQuery" placeholder="căutare semantică..." style="width: 300px;">
        <input type="text" id="searchDomain" placeholder="domeniu (opțional)" style="width: 200px;">
        <button onclick="semanticSearch()">🔍 Caută</button>
        <div id="searchResult"></div>
    </div>
    
    <script>
        function loadStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('status').innerHTML = 
                        `<div class="status">✅ Endpoints activi: ${data.active_endpoints}/${data.total_endpoints}</div>
                         <div>📄 Documente MongoDB: ${data.mongodb_documents}</div>
                         <div>🔍 Embeddings Qdrant: ${data.qdrant_embeddings}</div>
                         <div>💾 Cache mărime: ${data.cache_size}</div>`;
                })
                .catch(e => {
                    document.getElementById('status').innerHTML = '<div class="error">Eroare la încărcarea statusului</div>';
                });
        }
        
        function analyzeSite() {
            const url = document.getElementById('siteUrl').value;
            const question = document.getElementById('question').value || 'Ce oferă această companie?';
            
            if (!url) {
                alert('Te rog introduce un URL');
                return;
            }
            
            document.getElementById('analysisResult').innerHTML = '<div class="loading">Se analizează...</div>';
            
            fetch('/api/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url: url, question: question})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('analysisResult').innerHTML = 
                        `<div class="result">
                            <h3>✅ Analiză completă pentru: ${data.url}</h3>
                            <h4>📋 Plan GPT-4:</h4>
                            <pre>${JSON.stringify(data.plan, null, 2)}</pre>
                            <h4>🤖 Răspuns:</h4>
                            <p>${data.answer}</p>
                            <small>Timestamp: ${data.timestamp}</small>
                        </div>`;
                } else {
                    document.getElementById('analysisResult').innerHTML = 
                        `<div class="error">Eroare: ${data.error}</div>`;
                }
            })
            .catch(e => {
                document.getElementById('analysisResult').innerHTML = 
                    '<div class="error">Eroare la analiză</div>';
            });
        }
        
        function semanticSearch() {
            const query = document.getElementById('searchQuery').value;
            const domain = document.getElementById('searchDomain').value;
            
            if (!query) {
                alert('Te rog introduce o căutare');
                return;
            }
            
            document.getElementById('searchResult').innerHTML = '<div class="loading">Se caută...</div>';
            
            fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query, domain: domain, limit: 10})
            })
            .then(r => r.json())
            .then(data => {
                if (data.results && data.results.length > 0) {
                    let html = '<div class="result"><h3>🔍 Rezultate căutare semantică:</h3>';
                    data.results.forEach((result, i) => {
                        html += `<div style="border-bottom: 1px solid #eee; padding: 10px 0;">
                            <h4>${result.title}</h4>
                            <p><strong>Scor:</strong> ${result.score.toFixed(3)}</p>
                            <p><strong>Domeniu:</strong> ${result.domain}</p>
                            <p>${result.content.substring(0, 200)}...</p>
                            <small>URL: ${result.url}</small>
                        </div>`;
                    });
                    html += '</div>';
                    document.getElementById('searchResult').innerHTML = html;
                } else {
                    document.getElementById('searchResult').innerHTML = 
                        '<div class="result">Nu s-au găsit rezultate</div>';
                }
            })
            .catch(e => {
                document.getElementById('searchResult').innerHTML = 
                    '<div class="error">Eroare la căutare</div>';
            });
        }
        
        function runBenchmark() {
            document.getElementById('status').innerHTML = '<div class="loading">Se rulează benchmark...</div>';
            
            fetch('/api/benchmark', {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('status').innerHTML = '<div class="success">Benchmark completat!</div>';
                        setTimeout(loadStatus, 1000);
                    } else {
                        document.getElementById('status').innerHTML = `<div class="error">Eroare: ${data.error}</div>`;
                    }
                })
                .catch(e => {
                    document.getElementById('status').innerHTML = '<div class="error">Eroare la benchmark</div>';
                });
        }
        
        function generateEmbeddings() {
            document.getElementById('status').innerHTML = '<div class="loading">Se generează embeddings...</div>';
            
            fetch('/api/generate_embeddings', {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('status').innerHTML = '<div class="success">Generarea embeddings pornită în background!</div>';
                        setTimeout(loadStatus, 2000);
                    } else {
                        document.getElementById('status').innerHTML = `<div class="error">Eroare: ${data.error}</div>`;
                    }
                })
                .catch(e => {
                    document.getElementById('status').innerHTML = '<div class="error">Eroare la generarea embeddings</div>';
                });
        }
        
        // Încarcă statusul la pornire
        loadStatus();
        
        // Auto-refresh la fiecare 30 secunde
        setInterval(loadStatus, 30000);
    </script>
</body>
</html>
        ''')
    
    @app.route('/')
    def home():
        return '<h1>🚀 AI Pipeline API</h1><p><a href="/dashboard">📊 Accesează Dashboard-ul</a></p>'
    
    return app

if __name__ == "__main__":
    app = create_api_server()
    print("🚀 API Server pornit pe http://0.0.0.0:8080")
    print("📊 Dashboard la: http://0.0.0.0:8080/dashboard")
    app.run(host='0.0.0.0', port=8080, debug=False)
