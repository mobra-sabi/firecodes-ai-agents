import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class VerticalIndustrySolutions:
    def __init__(self):
        self.industries = {
            'medical_ai': {
                'potential': 'FOARTE MARE',
                'services': [
                    'Analiză imagini medicale (RMN, CT, Rx)',
                    'Transcrierea consultațiilor medicale',
                    'Asistent AI pentru diagnose',
                    'Procesare rezultate analize'
                ],
                'pricing': '1000-50000 RON/lună per clinică',
                'gpu_intensity': 'MAXIMĂ',
                'target_clients': 'Spitale, clinici private, cabinete medicale'
            },
            
            'legal_ai': {
                'potential': 'MARE',
                'services': [
                    'Analiză contracte automate',
                    'Research juridic AI',
                    'Redactare documente legale',
                    'Due diligence automat'
                ],
                'pricing': '500-10000 RON/lună per firmă',
                'gpu_intensity': 'MARE',
                'target_clients': 'Cabinete de avocatură, departamente juridice'
            },
            
            'finance_ai': {
                'potential': 'FOARTE MARE', 
                'services': [
                    'Analiză risc credit automat',
                    'Detectare fraudă în timp real',
                    'Trading algorithms',
                    'Compliance monitoring',
                    'Procesare formulare KYC'
                ],
                'pricing': '2000-100000 RON/lună',
                'gpu_intensity': 'MAXIMĂ',
                'target_clients': 'Bănci, IFN-uri, companii de asigurări'
            },
            
            'education_ai': {
                'potential': 'MARE',
                'services': [
                    'Tutori AI personalizați',
                    'Corectare automată teste',
                    'Generare conținut educațional',
                    'Analiză progres studenți'
                ],
                'pricing': '100-5000 RON/lună per instituție',
                'gpu_intensity': 'MEDIE',
                'target_clients': 'Universități, școli, platforme e-learning'
            },
            
            'retail_ai': {
                'potential': 'MARE',
                'services': [
                    'Recomandări produse personalizate',
                    'Optimizare prețuri dinamice',
                    'Analiză comportament clienți',
                    'Inventory management AI',
                    'Visual search pentru produse'
                ],
                'pricing': '300-10000 RON/lună',
                'gpu_intensity': 'MARE',
                'target_clients': 'Magazine online, retail chains, marketplaces'
            },
            
            'manufacturing_ai': {
                'potential': 'FOARTE MARE',
                'services': [
                    'Predictive maintenance',
                    'Quality control automat',
                    'Optimizare procese producție',
                    'Supply chain optimization',
                    'Detectare defecte în timp real'
                ],
                'pricing': '1000-50000 RON/lună per fabrică',
                'gpu_intensity': 'MAXIMĂ',
                'target_clients': 'Fabrici, unități de producție, industria auto'
            }
        }
        
    def get_industry_roadmap(self, industry):
        """Roadmap pentru implementare în industrie specifică"""
        roadmaps = {
            'medical_ai': {
                'phase1': 'Transcripție consultații medicale',
                'phase2': 'Analiză rezultate de laborator',
                'phase3': 'Asistent diagnostic AI',
                'timeline': '3-12 luni',
                'investment_needed': '50000-500000 RON'
            },
            'legal_ai': {
                'phase1': 'Analiză contracte simple',
                'phase2': 'Research juridic automat',
                'phase3': 'Redactare documente complexe',
                'timeline': '2-8 luni',
                'investment_needed': '30000-300000 RON'
            }
        }
        return roadmaps.get(industry, {})
        
    def calculate_roi(self, industry, client_size):
        """Calculează ROI pentru client bazat pe industrie și dimensiune"""
        base_savings = {
            'medical_ai': 50000,  # Economii anuale în RON
            'legal_ai': 30000,
            'finance_ai': 100000,
            'education_ai': 20000,
            'retail_ai': 40000,
            'manufacturing_ai': 200000
        }
        
        size_multipliers = {
            'small': 1,
            'medium': 3,
            'large': 10,
            'enterprise': 50
        }
        
        annual_savings = base_savings.get(industry, 25000) * size_multipliers.get(client_size, 1)
        return {
            'annual_savings': annual_savings,
            'implementation_cost': annual_savings * 0.3,  # 30% din economii
            'roi_percentage': 233,  # 233% ROI în primul an
            'payback_period': '3-6 luni'
        }
