#!/usr/bin/env python3
"""
API Endpoints pentru rapoarte CEO Workflow
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pymongo import MongoClient
from bson import ObjectId
from pathlib import Path
import sys

# Add reports to path
sys.path.insert(0, str(Path(__file__).parent.parent / "reports"))
from generator.report_generator import ReportGenerator
from utils.pdf_export import markdown_to_pdf

router = APIRouter(prefix="/api/reports", tags=["reports"])

# MongoDB
mongo = MongoClient('mongodb://localhost:27017/')
db = mongo.ai_agents_db


@router.get("/")
async def list_reports():
    """Listează toate rapoartele disponibile"""
    reports_dir = Path(__file__).parent.parent / "reports" / "output"
    reports = []
    
    for md_file in reports_dir.glob("*_report.md"):
        domain = md_file.stem.replace("_report", "")
        reports.append({
            "domain": domain,
            "markdown": str(md_file),
            "json": str(md_file.parent / f"{domain}_report.json"),
            "graph": str(md_file.parent / f"{domain}_graph.png"),
            "pdf": str(md_file.parent / f"{domain}_report.pdf") if (md_file.parent / f"{domain}_report.pdf").exists() else None,
        })
    
    return {"reports": reports}


@router.get("/{domain}")
async def get_report(domain: str, format: str = Query("json", regex="^(json|markdown|pdf|graph)$")):
    """Obține raport pentru un domain"""
    reports_dir = Path(__file__).parent.parent / "reports" / "output"
    
    if format == "json":
        json_file = reports_dir / f"{domain}_report.json"
        if not json_file.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        return FileResponse(json_file, media_type="application/json")
    
    elif format == "markdown":
        md_file = reports_dir / f"{domain}_report.md"
        if not md_file.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        return FileResponse(md_file, media_type="text/markdown")
    
    elif format == "pdf":
        pdf_file = reports_dir / f"{domain}_report.pdf"
        if not pdf_file.exists():
            # Generează PDF din Markdown
            md_file = reports_dir / f"{domain}_report.md"
            if not md_file.exists():
                raise HTTPException(status_code=404, detail="Report not found")
            pdf_file = markdown_to_pdf(md_file)
            if not pdf_file:
                raise HTTPException(status_code=500, detail="PDF generation failed")
        return FileResponse(pdf_file, media_type="application/pdf", filename=f"{domain}_report.pdf")
    
    elif format == "graph":
        png_file = reports_dir / f"{domain}_graph.png"
        if not png_file.exists():
            raise HTTPException(status_code=404, detail="Graph not found")
        return FileResponse(png_file, media_type="image/png")


@router.post("/generate/{agent_id}")
async def generate_report_from_agent(agent_id: str):
    """Generează raport din agent ID (creează log temporar din MongoDB)"""
    # Găsește agentul
    agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Găsește slave-ii
    slaves = list(db.site_agents.find({
        "master_agent_id": ObjectId(agent_id),
        "agent_type": "slave"
    }))
    
    # Creează log temporar
    from datetime import datetime
    log_content = f"""🎯 SITE TESTAT: {agent.get('site_url', 'N/A')}
📅 DATA: {datetime.now().isoformat()}
⏱️  DURATĂ TOTALĂ: N/A

════════════════════════════════════════════════════════════════
✅ REZULTATE FINALE
════════════════════════════════════════════════════════════════

1️⃣ AGENT MASTER CREAT:
   Domain: {agent.get('domain', 'N/A')}
   Status: {agent.get('status', 'unknown')}
   Agent Type: {agent.get('agent_type', 'master')}
   Chunks Indexed: {agent.get('chunks_indexed', 0)}
   Site URL: {agent.get('site_url', 'N/A')}
   Created: {agent.get('created_at', datetime.now().isoformat())}

2️⃣ SLAVE AGENTS CREAȚI:
   Total Slave Agents: {len(slaves)}
"""
    
    for i, slave in enumerate(slaves, 1):
        log_content += f"""
     {i}. {slave.get('domain', 'N/A')}
      - Status: {slave.get('status', 'unknown')}
      - Chunks: {slave.get('chunks_indexed', 0)}
      - Site URL: {slave.get('site_url', 'N/A')}
"""
    
    total_chunks = agent.get('chunks_indexed', 0) + sum(s.get('chunks_indexed', 0) for s in slaves)
    validated = sum(1 for s in slaves if s.get('status') == 'validated')
    created = sum(1 for s in slaves if s.get('status') == 'created')
    
    log_content += f"""
════════════════════════════════════════════════════════════════
📊 STATISTICI FINALE
════════════════════════════════════════════════════════════════
   Total Agents: {1 + len(slaves)} (1 master + {len(slaves)} slave)
   Total Chunks: {total_chunks}
   Master Chunks: {agent.get('chunks_indexed', 0)}
   Slave Chunks: {sum(s.get('chunks_indexed', 0) for s in slaves)}
   Validated Slaves: {validated}
   Created Slaves (în progres): {created}
"""
    
    # Salvează log temporar
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(log_content)
        temp_log = f.name
    
    # Generează raport
    try:
        generator = ReportGenerator(temp_log)
        results = generator.generate_all()
        
        return {
            "success": True,
            "domain": agent.get('domain'),
            "files": {
                "markdown": str(results.get("markdown")),
                "json": str(results.get("json")),
                "graph": str(results.get("graph")),
            }
        }
    finally:
        # Șterge log temporar
        Path(temp_log).unlink(missing_ok=True)

