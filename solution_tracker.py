# solution_tracker.py
"""
Sistem de tracking pentru soluțiile implementate și "sigilarea" problemelor rezolvate.
Acest sistem previne revenirea la aceleași probleme și menține contextul soluțiilor.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

class SolutionStatus(Enum):
    """Status-ul unei soluții"""
    ACTIVE = "active"           # Soluția funcționează
    SEALED = "sealed"           # Soluția este sigilată (nu se mai modifică)
    DEPRECATED = "deprecated"   # Soluția este înlocuită
    FAILED = "failed"           # Soluția a eșuat

@dataclass
class Solution:
    """O soluție implementată"""
    id: str
    problem: str
    solution: str
    status: SolutionStatus
    created_at: datetime
    sealed_at: Optional[datetime] = None
    test_results: List[Dict] = None
    files_modified: List[str] = None
    notes: str = ""
    
    def __post_init__(self):
        if self.test_results is None:
            self.test_results = []
        if self.files_modified is None:
            self.files_modified = []

class SolutionTracker:
    """Tracker pentru soluțiile implementate"""
    
    def __init__(self, storage_file: str = "solutions_tracker.json"):
        self.storage_file = storage_file
        self.solutions: Dict[str, Solution] = {}
        self.load_solutions()
    
    def load_solutions(self):
        """Încarcă soluțiile din fișier"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for solution_id, solution_data in data.items():
                        # Convertim datetime strings înapoi la datetime objects
                        solution_data['created_at'] = datetime.fromisoformat(solution_data['created_at'])
                        if solution_data.get('sealed_at'):
                            solution_data['sealed_at'] = datetime.fromisoformat(solution_data['sealed_at'])
                        solution_data['status'] = SolutionStatus(solution_data['status'])
                        self.solutions[solution_id] = Solution(**solution_data)
            except Exception as e:
                print(f"❌ Eroare la încărcarea soluțiilor: {e}")
                self.solutions = {}
    
    def save_solutions(self):
        """Salvează soluțiile în fișier"""
        try:
            data = {}
            for solution_id, solution in self.solutions.items():
                solution_dict = asdict(solution)
                # Convertim datetime objects în strings pentru JSON
                solution_dict['created_at'] = solution.created_at.isoformat()
                if solution.sealed_at:
                    solution_dict['sealed_at'] = solution.sealed_at.isoformat()
                solution_dict['status'] = solution.status.value
                data[solution_id] = solution_dict
            
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Eroare la salvarea soluțiilor: {e}")
    
    def add_solution(self, problem: str, solution: str, files_modified: List[str] = None, notes: str = "") -> str:
        """Adaugă o nouă soluție"""
        solution_id = f"sol_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        new_solution = Solution(
            id=solution_id,
            problem=problem,
            solution=solution,
            status=SolutionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            files_modified=files_modified or [],
            notes=notes
        )
        
        self.solutions[solution_id] = new_solution
        self.save_solutions()
        
        print(f"✅ Soluție adăugată: {solution_id}")
        return solution_id
    
    def seal_solution(self, solution_id: str, test_results: List[Dict] = None, notes: str = ""):
        """Sigilează o soluție (o marchează ca fiind finalizată și funcțională)"""
        if solution_id not in self.solutions:
            print(f"❌ Soluția {solution_id} nu există")
            return False
        
        solution = self.solutions[solution_id]
        solution.status = SolutionStatus.SEALED
        solution.sealed_at = datetime.now(timezone.utc)
        if test_results:
            solution.test_results = test_results
        if notes:
            solution.notes = notes
        
        self.save_solutions()
        print(f"🔒 Soluția {solution_id} a fost SIGILATĂ")
        return True
    
    def check_sealed_solution(self, problem: str) -> Optional[Solution]:
        """Verifică dacă există o soluție sigilată pentru această problemă"""
        for solution in self.solutions.values():
            if (solution.status == SolutionStatus.SEALED and 
                problem.lower() in solution.problem.lower()):
                return solution
        return None
    
    def get_active_solutions(self) -> List[Solution]:
        """Returnează toate soluțiile active"""
        return [s for s in self.solutions.values() if s.status == SolutionStatus.ACTIVE]
    
    def get_sealed_solutions(self) -> List[Solution]:
        """Returnează toate soluțiile sigilate"""
        return [s for s in self.solutions.values() if s.status == SolutionStatus.SEALED]
    
    def mark_deprecated(self, solution_id: str, replacement_id: str = None, notes: str = ""):
        """Marchează o soluție ca fiind înlocuită"""
        if solution_id not in self.solutions:
            print(f"❌ Soluția {solution_id} nu există")
            return False
        
        solution = self.solutions[solution_id]
        solution.status = SolutionStatus.DEPRECATED
        if notes:
            solution.notes = notes
        if replacement_id:
            solution.notes += f" | Înlocuită de: {replacement_id}"
        
        self.save_solutions()
        print(f"⚠️ Soluția {solution_id} a fost marcată ca DEPRECATED")
        return True
    
    def get_solution_summary(self) -> Dict[str, Any]:
        """Returnează un sumar al soluțiilor"""
        total = len(self.solutions)
        active = len(self.get_active_solutions())
        sealed = len(self.get_sealed_solutions())
        deprecated = len([s for s in self.solutions.values() if s.status == SolutionStatus.DEPRECATED])
        
        return {
            "total": total,
            "active": active,
            "sealed": sealed,
            "deprecated": deprecated,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    def print_status(self):
        """Afișează statusul soluțiilor"""
        summary = self.get_solution_summary()
        print(f"\n📊 STATUS SOLUȚII:")
        print(f"   Total: {summary['total']}")
        print(f"   Active: {summary['active']}")
        print(f"   Sigilate: {summary['sealed']}")
        print(f"   Deprecated: {summary['deprecated']}")
        
        if self.get_sealed_solutions():
            print(f"\n🔒 SOLUȚII SIGILATE:")
            for solution in self.get_sealed_solutions():
                print(f"   {solution.id}: {solution.problem[:50]}...")

# Instanță globală
solution_tracker = SolutionTracker()

# Funcții de conveniență
def add_solution(problem: str, solution: str, files_modified: List[str] = None, notes: str = "") -> str:
    """Adaugă o soluție nouă"""
    return solution_tracker.add_solution(problem, solution, files_modified, notes)

def seal_solution(solution_id: str, test_results: List[Dict] = None, notes: str = ""):
    """Sigilează o soluție"""
    return solution_tracker.seal_solution(solution_id, test_results, notes)

def check_sealed_solution(problem: str) -> Optional[Solution]:
    """Verifică dacă există o soluție sigilată pentru această problemă"""
    return solution_tracker.check_sealed_solution(problem)

def get_solution_summary() -> Dict[str, Any]:
    """Returnează sumarul soluțiilor"""
    return solution_tracker.get_solution_summary()

def print_solution_status():
    """Afișează statusul soluțiilor"""
    solution_tracker.print_status()

# Decorator pentru verificarea soluțiilor sigilate
def check_sealed_before_action(problem_description: str):
    """Decorator care verifică dacă există o soluție sigilată înainte de a executa o acțiune"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            sealed_solution = check_sealed_solution(problem_description)
            if sealed_solution:
                print(f"🔒 SOLUȚIE SIGILATĂ GĂSITĂ pentru: {problem_description}")
                print(f"   Soluția: {sealed_solution.solution}")
                print(f"   Sigilată la: {sealed_solution.sealed_at}")
                print(f"   Nu se execută acțiunea - soluția este deja implementată și funcțională")
                return sealed_solution
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

