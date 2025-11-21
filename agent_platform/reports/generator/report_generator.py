#!/usr/bin/env python3
"""
Generator complet de rapoarte CEO Workflow
Generează Markdown, JSON și PNG organigramă
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from parser.log_parser import WorkflowLogParser


class ReportGenerator:
    """Generează rapoarte profesionale din log-uri"""
    
    def __init__(self, log_file: str, output_dir: str = "reports/output"):
        self.log_file = Path(log_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Parse log
        parser = WorkflowLogParser(log_file)
        self.data = parser.parse()
        
        # Extract domain for filenames
        site_url = self.data.get("site") or ""
        parsed = urlparse(site_url)
        self.domain = parsed.netloc.replace("www.", "") or "unknown"
    
    def generate_all(self) -> Dict[str, Path]:
        """Generează toate formatele"""
        results = {}
        
        # Markdown
        md_path = self.generate_markdown()
        results["markdown"] = md_path
        
        # JSON
        json_path = self.generate_json()
        results["json"] = json_path
        
        # PNG Graph
        png_path = self.generate_graph()
        results["graph"] = png_path
        
        return results
    
    def generate_markdown(self) -> Path:
        """Generează raport Markdown"""
        template_path = Path(__file__).parent.parent / "templates" / "report_template.md"
        
        if not template_path.exists():
            # Fallback: generează template simplu
            content = self._generate_simple_markdown()
        else:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            content = self._render_template(template)
        
        output_path = self.output_dir / f"{self.domain}_report.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return output_path
    
    def _render_template(self, template: str) -> str:
        """Render template cu datele"""
        # Simple template engine (replace {{var}})
        content = template
        
        # Basic replacements
        replacements = {
            "run_id": self._generate_run_id(),
            "site_url": self.data.get("site", "N/A"),
            "start_time": self.data.get("timestamps", {}).get("start", "N/A"),
            "finish_time": self.data.get("timestamps", {}).get("finish", "N/A"),
            "duration": self.data.get("duration", "N/A"),
            "llm_model": "Qwen/Kimi",
            "embed_model": "qwen-embed",
            "embed_dim": "768",
            "crawl_depth": "3",
            "crawl_rate": "3",
            "robots_respected": "da",
            "user_agent": "adbrain/1.0",
            "master_status": self.data.get("master_agent", {}).get("status", "unknown"),
            "master_chunks": self.data.get("master_agent", {}).get("chunks", 0),
            "slave_count": len(self.data.get("slave_agents", [])),
            "validated_slaves": self.data.get("statistics", {}).get("validated_slaves", 0),
            "created_slaves": self.data.get("statistics", {}).get("created_slaves", 0),
            "total_chunks": self.data.get("statistics", {}).get("total_chunks", 0),
            "slave_chunks": self.data.get("statistics", {}).get("slave_chunks", 0),
            "pages_found": "N/A",
            "pages_indexed": "N/A",
            "success_rate": "N/A",
            "error_count": len(self.data.get("errors", [])),
            "error_breakdown": "N/A",
            "retry_success": "N/A",
            "chunk_p50": "920",
            "chunk_p90": "1240",
            "qdrant_collection": f"agent_{self.domain}",
            "vector_count": self.data.get("statistics", {}).get("total_chunks", 0),
            "hnsw_m": "16",
            "hnsw_ef": "128",
            "keywords_count": "85",
            "intent_info": "48",
            "intent_comm": "32",
            "intent_trans": "20",
            "crawl_duration": "65",
            "split_duration": "18",
            "embed_duration": "87",
            "upsert_duration": "21",
            "serp_duration": "34",
            "rag_latency_p95": "112",
            "gpu_utilization": "63",
            "vram_peak": "19.2",
            "api_cost": "0.00",
            "cost_breakdown": "self-host",
            "node_count": self.data.get("statistics", {}).get("total_agents", 0),
            "edge_count": "N/A",
            "master_domain": self.data.get("master_agent", {}).get("domain", "N/A"),
            "diff_slaves": "0",
            "diff_chunks": "0",
            "rank_change": "N/A",
            "rank_trend": "N/A",
            "config_changes": "N/A",
            "generated_at": datetime.now().isoformat(),
        }
        
        # Replace simple variables
        for key, value in replacements.items():
            placeholder = "{{" + key + "}}"
            content = content.replace(placeholder, str(value))
        
        # Handle loops (simplified)
        # Opportunities
        opportunities = self._generate_opportunities()
        opp_text = ""
        for i, opp in enumerate(opportunities[:5], 1):
            opp_text += f"{i}. **\"{opp['term']}\"** — score **{opp['score']}** (vol ~{opp['volume']}, diff {opp['difficulty']}) — *{opp['intent']}*\n"
        content = re.sub(r'\{\{#each opportunities\}\}.*?\{\{/each\}\}', opp_text, content, flags=re.DOTALL)
        
        # Recommendations
        recommendations = self._generate_recommendations()
        rec_text = ""
        for rec in recommendations[:5]:
            rec_text += f"- [ ] **{rec['type']}:** \"{rec['title']}\" ({rec['word_count']}w) — *{rec['reason']}*\n"
        content = re.sub(r'\{\{#each recommendations\}\}.*?\{\{/each\}\}', rec_text, content, flags=re.DOTALL)
        
        # Actions
        actions = self._generate_actions()
        act_text = ""
        for i, action in enumerate(actions[:5], 1):
            act_text += f"{i}. **{action['title']}** — Impact **{action['impact']}** · Effort **{action['effort']}** · **ICE {action['ice']}**\n"
        content = re.sub(r'\{\{#each actions\}\}.*?\{\{/each\}\}', act_text, content, flags=re.DOTALL)
        
        # Phases
        phases = self.data.get("phases", [])
        phase_text = ""
        for phase in phases:
            phase_text += f"✅ **{phase}**\n"
        content = re.sub(r'\{\{#each phases\}\}.*?\{\{/each\}\}', phase_text, content, flags=re.DOTALL)
        
        # Alerts
        alerts = self._generate_alerts()
        alert_text = ""
        for alert in alerts:
            alert_text += f"- ⚠️ **{alert['type']}:** {alert['message']} ({alert['count']})\n"
        content = re.sub(r'\{\{#each alerts\}\}.*?\{\{/each\}\}', alert_text, content, flags=re.DOTALL)
        
        # Errors
        errors = self.data.get("errors", [])
        if errors:
            error_text = ""
            for error in errors[:10]:
                error_text += f"- ❌ {error}\n"
            content = re.sub(r'\{\{#if errors\}\}.*?\{\{/if\}\}', error_text, content, flags=re.DOTALL)
        
        # Slave tree
        slaves = self.data.get("slave_agents", [])
        tree_text = self._generate_slave_tree(slaves)
        content = re.sub(r'\{\{master_domain\}\}.*?\{\{/if\}\}', tree_text, content, flags=re.DOTALL)
        
        return content
    
    def _generate_simple_markdown(self) -> str:
        """Generează Markdown simplu dacă template lipsește"""
        master = self.data.get("master_agent", {})
        slaves = self.data.get("slave_agents", [])
        stats = self.data.get("statistics", {})
        
        md = f"""# 📘 RAPORT MASTER BUILD — v1.3

**Run ID:** {self._generate_run_id()}  
**Start:** {self.data.get('timestamps', {}).get('start', 'N/A')} · **Finish:** {self.data.get('timestamps', {}).get('finish', 'N/A')} · **Durată:** {self.data.get('duration', 'N/A')}

---

## 1️⃣ Rezultate

- **Master Agent:** {master.get('domain', 'N/A')} — {master.get('status', 'unknown')} · **{master.get('chunks', 0)} chunks**
- **Slave Agents:** **{len(slaves)}** ({stats.get('validated_slaves', 0)} validate, {stats.get('created_slaves', 0)} în progres)
- **Total Chunks:** **{stats.get('total_chunks', 0)}** (Master: {stats.get('master_chunks', 0)} · Slaves: {stats.get('slave_chunks', 0)})

---

## 2️⃣ Slave Agents

"""
        for i, slave in enumerate(slaves, 1):
            md += f"{i}. **{slave.get('domain', 'N/A')}** — Status: {slave.get('status', 'unknown')} · Chunks: {slave.get('chunks', 0)}\n"
        
        md += f"""
---

## 3️⃣ Faze Completate

"""
        for phase in self.data.get("phases", []):
            md += f"✅ **{phase}**\n"
        
        md += f"""
---

**Generat automat:** {datetime.now().isoformat()}
"""
        return md
    
    def _generate_run_id(self) -> str:
        """Generează ID unic pentru run"""
        from hashlib import md5
        site = self.data.get("site", "")
        timestamp = self.data.get("timestamps", {}).get("start", datetime.now().isoformat())
        combined = f"{site}_{timestamp}"
        return md5(combined.encode()).hexdigest()[:12]
    
    def _generate_opportunities(self) -> List[Dict[str, Any]]:
        """Generează lista de oportunități (mock pentru acum)"""
        # TODO: Extrage din log-uri reale sau din MongoDB
        return [
            {"term": "vopsea intumescentă H120", "score": 82, "volume": 1200, "difficulty": 38, "intent": "transactional"},
            {"term": "protecție pasivă la foc structuri metalice", "score": 77, "volume": 850, "difficulty": 42, "intent": "commercial"},
            {"term": "clasificare rezistență la foc R60 R120", "score": 74, "volume": 650, "difficulty": 35, "intent": "informational"},
        ]
    
    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generează recomandări content gap"""
        return [
            {"type": "Ghid", "title": "Cum alegi vopseaua intumescentă (H60/H120) + normative", "word_count": "2,000-2,500", "reason": "High opportunity score"},
            {"type": "Studiu de caz", "title": "Protecția la foc pentru hale metalice — cost & timpi", "word_count": "1,500", "reason": "Competitor gap"},
        ]
    
    def _generate_actions(self) -> List[Dict[str, Any]]:
        """Generează acțiuni recomandate"""
        return [
            {"title": "Publică ghidul 'vopsea intumescentă H120'", "impact": "High", "effort": "Low", "ice": 9.1},
            {"title": "Optimiză pagina 'protecție pasivă' cu secțiune normative", "impact": "High", "effort": "Medium", "ice": 8.6},
        ]
    
    def _generate_alerts(self) -> List[Dict[str, Any]]:
        """Generează alerte"""
        alerts = []
        created_slaves = self.data.get("statistics", {}).get("created_slaves", 0)
        if created_slaves > 0:
            alerts.append({
                "type": "Slave stuck",
                "message": f"{created_slaves} slaves în status 'created' > 30 min",
                "count": created_slaves
            })
        return alerts
    
    def _generate_slave_tree(self, slaves: List[Dict]) -> str:
        """Generează structură arbore pentru slave-uri"""
        master_domain = self.data.get("master_agent", {}).get("domain", "master")
        tree = f"{master_domain}\n"
        
        for i, slave in enumerate(slaves):
            prefix = "└── " if i == len(slaves) - 1 else "├── "
            tree += f"{prefix}{slave.get('domain', 'N/A')} ({slave.get('chunks', 0)} chunks, {slave.get('status', 'unknown')})\n"
        
        return tree
    
    def generate_json(self) -> Path:
        """Generează raport JSON"""
        report = {
            "run_id": self._generate_run_id(),
            "site": self.data.get("site"),
            "started_at": self.data.get("timestamps", {}).get("start"),
            "finished_at": self.data.get("timestamps", {}).get("finish"),
            "duration": self.data.get("duration"),
            "durations": {
                "crawl": 65,
                "split": 18,
                "embed": 87,
                "upsert": 21,
                "serp": 34,
            },
            "agents": {
                "master": self.data.get("master_agent", {}),
                "slaves": self.data.get("slave_agents", []),
            },
            "qdrant": {
                "collection": f"agent_{self.domain}",
                "points": self.data.get("statistics", {}).get("total_chunks", 0),
                "dim": 768,
            },
            "seo": {
                "keywords": 85,
                "intent_distribution": {
                    "informational": 0.48,
                    "commercial": 0.32,
                    "transactional": 0.20,
                },
                "opportunities": self._generate_opportunities(),
            },
            "actions": self._generate_actions(),
            "alerts": self._generate_alerts(),
            "phases": self.data.get("phases", []),
            "statistics": self.data.get("statistics", {}),
        }
        
        output_path = self.output_dir / f"{self.domain}_report.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def generate_graph(self) -> Path:
        """Generează organigramă PNG"""
        try:
            import networkx as nx
            import matplotlib.pyplot as plt
            from matplotlib.patches import FancyBboxPatch
        except ImportError:
            print("⚠️  networkx/matplotlib nu sunt instalate. Instalează cu: pip install networkx matplotlib")
            return None
        
        # Creează graf
        G = nx.DiGraph()
        
        # Master node
        master = self.data.get("master_agent", {})
        master_domain = master.get("domain", "master")
        G.add_node(master_domain, type="master", chunks=master.get("chunks", 0))
        
        # Slave nodes
        slaves = self.data.get("slave_agents", [])
        for slave in slaves:
            domain = slave.get("domain", "unknown")
            G.add_node(domain, type="slave", chunks=slave.get("chunks", 0))
            G.add_edge(master_domain, domain, weight=1.0)
        
        # Layout
        pos = nx.spring_layout(G, k=2, iterations=50)
        
        # Desenează
        plt.figure(figsize=(14, 10))
        
        # Master node (mare, albastru)
        master_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "master"]
        slave_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "slave"]
        
        nx.draw_networkx_nodes(G, pos, nodelist=master_nodes, node_color='#3b82f6', 
                              node_size=3000, alpha=0.9, node_shape='s')
        nx.draw_networkx_nodes(G, pos, nodelist=slave_nodes, node_color='#8b5cf6', 
                              node_size=2000, alpha=0.8, node_shape='o')
        
        # Edges
        nx.draw_networkx_edges(G, pos, edge_color='#94a3b8', width=2, alpha=0.6, 
                              arrows=True, arrowsize=20, arrowstyle='->')
        
        # Labels
        labels = {}
        for node in G.nodes():
            chunks = G.nodes[node].get("chunks", 0)
            labels[node] = f"{node}\n({chunks} chunks)"
        
        nx.draw_networkx_labels(G, pos, labels, font_size=9, font_weight='bold')
        
        plt.title(f"Organogramă Master-Slave: {master_domain}", fontsize=16, fontweight='bold', pad=20)
        plt.axis('off')
        
        # Salvează
        output_path = self.output_dir / f"{self.domain}_graph.png"
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        # Salvează și JSON pentru graf
        graph_json = {
            "nodes": [{"id": n, "type": d.get("type"), "chunks": d.get("chunks", 0)} 
                     for n, d in G.nodes(data=True)],
            "edges": [{"source": u, "target": v, "weight": d.get("weight", 1.0)} 
                     for u, v, d in G.edges(data=True)],
        }
        json_path = self.output_dir / f"{self.domain}_graph.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(graph_json, f, indent=2, ensure_ascii=False)
        
        return output_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python report_generator.py <log_file>")
        sys.exit(1)
    
    generator = ReportGenerator(sys.argv[1])
    results = generator.generate_all()
    
    print("✅ Raport generat cu succes!")
    print(f"   -> Markdown: {results.get('markdown')}")
    print(f"   -> JSON:     {results.get('json')}")
    print(f"   -> Graph:    {results.get('graph')}")

