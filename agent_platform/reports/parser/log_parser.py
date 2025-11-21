#!/usr/bin/env python3
"""
Parser pentru log-uri CEO Workflow
Extrage date structurate din log-uri text
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class WorkflowLogParser:
    """Parsează log-uri workflow și extrage date structurate"""
    
    def __init__(self, log_file: str):
        self.log_file = Path(log_file)
        self.content = self._read_log()
        self.parsed_data = {}
    
    def _read_log(self) -> str:
        """Citește log-ul"""
        with open(self.log_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def parse(self) -> Dict[str, Any]:
        """Parsează log-ul complet"""
        self.parsed_data = {
            "site": self._extract_site(),
            "date": self._extract_date(),
            "duration": self._extract_duration(),
            "master_agent": self._extract_master_agent(),
            "slave_agents": self._extract_slave_agents(),
            "phases": self._extract_phases(),
            "statistics": self._extract_statistics(),
            "errors": self._extract_errors(),
            "timestamps": self._extract_timestamps(),
        }
        return self.parsed_data
    
    def _extract_site(self) -> Optional[str]:
        """Extrage URL site"""
        match = re.search(r'SITE TESTAT:\s*(https?://[^\s]+)', self.content, re.IGNORECASE)
        if match:
            return match.group(1)
        # Fallback: căută în alte formate
        match = re.search(r'Site URL:\s*(https?://[^\s]+)', self.content, re.IGNORECASE)
        return match.group(1) if match else None
    
    def _extract_date(self) -> Optional[str]:
        """Extrage data"""
        match = re.search(r'📅\s*DATA:\s*([^\n]+)', self.content)
        if match:
            return match.group(1).strip()
        # Fallback: ISO date
        match = re.search(r'ISODate\([\'"](\d{4}-\d{2}-\d{2}T[^\']+)[\'"]', self.content)
        return match.group(1) if match else datetime.now().isoformat()
    
    def _extract_duration(self) -> Optional[str]:
        """Extrage durata"""
        match = re.search(r'⏱️\s*DURAT[ĂA]\s*TOTAL[ĂA]:\s*([^\n]+)', self.content)
        return match.group(1).strip() if match else None
    
    def _extract_master_agent(self) -> Dict[str, Any]:
        """Extrage informații master agent"""
        master = {
            "domain": None,
            "status": None,
            "chunks": 0,
            "site_url": None,
            "created_at": None,
        }
        
        # Căută secțiunea "AGENT MASTER CREAT"
        master_section = re.search(
            r'1️⃣\s*AGENT MASTER CREAT:.*?(?=2️⃣|═════|$)',
            self.content,
            re.DOTALL | re.IGNORECASE
        )
        
        if master_section:
            section = master_section.group(0)
            # Domain
            match = re.search(r'Domain:\s*([^\n]+)', section)
            if match:
                master["domain"] = match.group(1).strip()
            
            # Status
            match = re.search(r'Status:\s*([^\n]+)', section)
            if match:
                master["status"] = match.group(1).strip()
            
            # Chunks
            match = re.search(r'Chunks Indexed:\s*(\d+)', section)
            if match:
                master["chunks"] = int(match.group(1))
            
            # Site URL
            match = re.search(r'Site URL:\s*([^\n]+)', section)
            if match:
                master["site_url"] = match.group(1).strip()
            
            # Created
            match = re.search(r'Created:\s*([^\n]+)', section)
            if match:
                master["created_at"] = match.group(1).strip()
        
        return master
    
    def _extract_slave_agents(self) -> List[Dict[str, Any]]:
        """Extrage lista slave agents"""
        slaves = []
        
        # Căută secțiunea "SLAVE AGENTS CREAȚI"
        slave_section = re.search(
            r'2️⃣\s*SLAVE AGENTS CREAȚI:.*?(?=═════|📋|$)',
            self.content,
            re.DOTALL | re.IGNORECASE
        )
        
        if slave_section:
            section = slave_section.group(0)
            # Extrage fiecare slave (format: "1. domain | Status: ... | Chunks: ...")
            pattern = r'(\d+)\.\s*([^\n|]+)\s*\|\s*Status:\s*([^\n|]+)\s*\|\s*Chunks:\s*(\d+)'
            matches = re.finditer(pattern, section)
            
            for match in matches:
                slaves.append({
                    "domain": match.group(2).strip(),
                    "status": match.group(3).strip(),
                    "chunks": int(match.group(4)),
                    "site_url": None,  # Poate fi extras separat
                })
        
        # Fallback: căută în format alternativ
        if not slaves:
            pattern = r'(\d+)\.\s*([^\n]+)\s*- Status:\s*([^\n]+)\s*- Chunks:\s*(\d+)'
            matches = re.finditer(pattern, self.content)
            for match in matches:
                slaves.append({
                    "domain": match.group(2).strip(),
                    "status": match.group(3).strip(),
                    "chunks": int(match.group(4)),
                })
        
        # Extrage site_url-uri dacă există
        for slave in slaves:
            domain_escaped = re.escape(slave["domain"])
            url_pattern = rf'{domain_escaped}.*?Site URL:\s*([^\n]+)'
            match = re.search(url_pattern, self.content)
            if match:
                slave["site_url"] = match.group(1).strip()
        
        return slaves
    
    def _extract_phases(self) -> List[str]:
        """Extrage fazele completate"""
        phases = []
        # Căută "FAZA X COMPLETĂ" sau "Phase X completed"
        pattern = r'(?:FAZA|Phase)\s*(\d+)[/\d]*\s*(?:COMPLETĂ|completed|✅)'
        matches = re.finditer(pattern, self.content, re.IGNORECASE)
        for match in matches:
            phase_num = match.group(1)
            phases.append(f"Phase {phase_num}")
        return sorted(set(phases), key=lambda x: int(re.search(r'\d+', x).group()))
    
    def _extract_statistics(self) -> Dict[str, Any]:
        """Extrage statistici"""
        stats = {
            "total_agents": 0,
            "total_chunks": 0,
            "master_chunks": 0,
            "slave_chunks": 0,
            "validated_slaves": 0,
            "created_slaves": 0,
        }
        
        # Căută secțiunea "STATISTICI FINALE"
        stats_section = re.search(
            r'📊\s*STATISTICI FINALE.*?(?=═════|$)',
            self.content,
            re.DOTALL | re.IGNORECASE
        )
        
        if stats_section:
            section = stats_section.group(0)
            # Total Agents
            match = re.search(r'Total Agents:\s*(\d+)', section)
            if match:
                stats["total_agents"] = int(match.group(1))
            
            # Total Chunks
            match = re.search(r'Total Chunks:\s*(\d+)', section)
            if match:
                stats["total_chunks"] = int(match.group(1))
            
            # Master Chunks
            match = re.search(r'Master Chunks:\s*(\d+)', section)
            if match:
                stats["master_chunks"] = int(match.group(1))
            
            # Slave Chunks
            match = re.search(r'Slave Chunks:\s*(\d+)', section)
            if match:
                stats["slave_chunks"] = int(match.group(1))
            
            # Validated Slaves
            match = re.search(r'Validated Slaves:\s*(\d+)', section)
            if match:
                stats["validated_slaves"] = int(match.group(1))
            
            # Created Slaves
            match = re.search(r'Created Slaves.*?:\s*(\d+)', section)
            if match:
                stats["created_slaves"] = int(match.group(1))
        
        # Fallback: calculează din master + slaves dacă nu găsește
        if stats["total_agents"] == 0:
            master = self._extract_master_agent()
            slaves = self._extract_slave_agents()
            stats["total_agents"] = 1 + len(slaves)
            stats["master_chunks"] = master.get("chunks", 0)
            stats["slave_chunks"] = sum(s.get("chunks", 0) for s in slaves)
            stats["total_chunks"] = stats["master_chunks"] + stats["slave_chunks"]
            stats["validated_slaves"] = sum(1 for s in slaves if s.get("status") == "validated")
            stats["created_slaves"] = sum(1 for s in slaves if s.get("status") == "created")
        
        return stats
    
    def _extract_errors(self) -> List[str]:
        """Extrage erori"""
        errors = []
        # Căută linii cu ERROR sau Exception
        pattern = r'(?:ERROR|Exception|Failed|❌):\s*([^\n]+)'
        matches = re.finditer(pattern, self.content, re.IGNORECASE)
        for match in matches:
            errors.append(match.group(1).strip())
        return errors
    
    def _extract_timestamps(self) -> Dict[str, Optional[str]]:
        """Extrage timestamp-uri importante"""
        timestamps = {
            "start": None,
            "finish": None,
        }
        
        # Căută ISO dates
        iso_pattern = r'ISODate\([\'"](\d{4}-\d{2}-\d{2}T[^\']+)[\'"]'
        matches = list(re.finditer(iso_pattern, self.content))
        if matches:
            timestamps["start"] = matches[0].group(1)
            if len(matches) > 1:
                timestamps["finish"] = matches[-1].group(1)
        
        return timestamps


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python log_parser.py <log_file>")
        sys.exit(1)
    
    parser = WorkflowLogParser(sys.argv[1])
    data = parser.parse()
    print(json.dumps(data, indent=2, ensure_ascii=False))

