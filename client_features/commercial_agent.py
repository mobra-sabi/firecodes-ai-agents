import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database.mongodb_handler import MongoDBHandler
from datetime import datetime, timedelta
import json

class CommercialAgent:
    def __init__(self, site_url):
        self.site_url = site_url
        self.client_session = {}
        self.mongodb = MongoDBHandler()
        
    def advanced_features(self):
        return {
            'price_calculator': self.calculate_quotes,
            'appointment_scheduler': self.schedule_meetings,
            'document_generator': self.generate_proposals,
            'product_configurator': self.configure_services,
            'lead_qualification': self.qualify_leads
        }
        
    def calculate_quotes(self, project_details):
        """Calculează oferte bazate pe specificațiile proiectului"""
        
        # Template de bază pentru calculul ofertelor
        base_rates = {
            'vopsitorii_industriale': 50,  # ron/mp
            'reparatii_industriale': 100,  # ron/ora
            'reabilitare_silozuri': 200,   # ron/mp
            'constructii_industriale': 300 # ron/mp
        }
        
        try:
            service_type = project_details.get('service', 'general')
            area_size = float(project_details.get('area', 0))
            complexity = project_details.get('complexity', 'normal')  # simple, normal, complex
            
            # Factor de complexitate
            complexity_multiplier = {
                'simple': 0.8,
                'normal': 1.0,
                'complex': 1.3
            }
            
            base_price = base_rates.get(service_type, 100) * area_size
            final_price = base_price * complexity_multiplier.get(complexity, 1.0)
            
            quote = {
                'service': service_type,
                'area': area_size,
                'complexity': complexity,
                'base_price': base_price,
                'final_price': final_price,
                'currency': 'RON',
                'validity': '30 zile',
                'generated_at': str(datetime.now())
            }
            
            # Salvează oferta în baza de date
            self.save_quote(quote)
            
            return quote
            
        except Exception as e:
            return {'error': f'Eroare la calculul ofertei: {str(e)}'}
    
    def schedule_meetings(self, availability):
        """Programează întâlniri automat"""
        
        # Orele disponibile (simulare)
        available_slots = [
            '09:00-10:00', '10:00-11:00', '11:00-12:00',
            '14:00-15:00', '15:00-16:00', '16:00-17:00'
        ]
        
        client_preferences = availability.get('preferred_time', 'morning')
        date_requested = availability.get('date', str(datetime.now().date()))
        
        if client_preferences == 'morning':
            suggested_slots = available_slots[:3]
        else:
            suggested_slots = available_slots[3:]
            
        meeting = {
            'date': date_requested,
            'suggested_slots': suggested_slots,
            'client_info': availability.get('client_info', {}),
            'status': 'pending',
            'created_at': str(datetime.now())
        }
        
        # Salvează programarea
        self.save_appointment(meeting)
        
        return meeting
    
    def generate_proposals(self, requirements):
        """Generează propuneri comerciale personalizate"""
        
        proposal_template = f"""
PROPUNERE COMERCIALĂ
{self.get_company_name()}

Stimată/Stimate {requirements.get('client_name', 'Client')},

În baza discuțiilor avute, vă prezentăm următoarea propunere:

SERVICII PROPUSE:
{self.format_services(requirements.get('services', []))}

AVANTAJELE NOASTRE:
• Experiență de peste 10 ani în domeniu
• Echipă tehnică specializată
• Certificări și standarde de calitate
• Garanție extinsă pentru lucrări

PERIOADA DE EXECUȚIE: {requirements.get('timeline', '2-4 săptămâni')}

VALIDITATEA OFERTEI: 30 zile

Pentru detalii suplimentare, vă rugăm să ne contactați.

Cu stimă,
Echipa {self.get_company_name()}
"""
        
        proposal = {
            'content': proposal_template,
            'client_name': requirements.get('client_name'),
            'services': requirements.get('services'),
            'generated_at': str(datetime.now()),
            'status': 'draft'
        }
        
        self.save_proposal(proposal)
        return proposal
    
    def configure_services(self, service_requirements):
        """Configurează serviciile bazat pe cerințele clientului"""
        
        service_catalog = {
            'vopsitorii_industriale': {
                'options': ['intumescent', 'anticoroziv', 'decorativ'],
                'colors': ['RAL 1015', 'RAL 3000', 'RAL 5010', 'RAL 7035'],
                'finishes': ['mat', 'semi-mat', 'lucios']
            },
            'reparatii_industriale': {
                'types': ['mecanice', 'structurale', 'preventive'],
                'urgency': ['normală', 'urgentă', 'critică']
            },
            'constructii_industriale': {
                'materials': ['beton', 'metal', 'mixt'],
                'certifications': ['FROSIO', 'ISO 9001', 'ISO 14001']
            }
        }
        
        service_type = service_requirements.get('type')
        configuration = service_catalog.get(service_type, {})
        
        return {
            'service_type': service_type,
            'available_options': configuration,
            'recommended_config': self.get_recommended_config(service_requirements),
            'estimated_duration': self.estimate_duration(service_requirements)
        }
    
    def qualify_leads(self, client_info):
        """Califică leadurile bazat pe conversație"""
        
        scoring_criteria = {
            'budget_range': client_info.get('budget', 0),
            'project_size': client_info.get('project_size', 'small'),
            'timeline': client_info.get('timeline', 'flexible'),
            'decision_maker': client_info.get('is_decision_maker', False),
            'previous_experience': client_info.get('has_experience', False)
        }
        
        # Calculează scorul
        score = 0
        
        # Buget (0-30 puncte)
        budget = scoring_criteria['budget_range']
        if budget > 50000:
            score += 30
        elif budget > 20000:
            score += 20
        elif budget > 5000:
            score += 10
            
        # Dimensiunea proiectului (0-25 puncte)
        project_size = scoring_criteria['project_size']
        if project_size == 'large':
            score += 25
        elif project_size == 'medium':
            score += 15
        elif project_size == 'small':
            score += 10
            
        # Timeline (0-20 puncte)
        timeline = scoring_criteria['timeline']
        if timeline == 'urgent':
            score += 20
        elif timeline == 'soon':
            score += 15
        elif timeline == 'flexible':
            score += 10
            
        # Decision maker (0-15 puncte)
        if scoring_criteria['decision_maker']:
            score += 15
            
        # Experiență anterioară (0-10 puncte)
        if scoring_criteria['previous_experience']:
            score += 10
            
        # Clasificare lead
        if score >= 80:
            lead_quality = 'A - Prioritate maximă'
        elif score >= 60:
            lead_quality = 'B - Prioritate mare'
        elif score >= 40:
            lead_quality = 'C - Prioritate medie'
        else:
            lead_quality = 'D - Prioritate scăzută'
            
        lead_qualification = {
            'score': score,
            'quality': lead_quality,
            'criteria': scoring_criteria,
            'recommended_actions': self.get_recommended_actions(score),
            'qualified_at': str(datetime.now())
        }
        
        self.save_lead_qualification(lead_qualification)
        return lead_qualification
    
    # Metode helper
    def get_company_name(self):
        site_context = self.mongodb.get_site_content(self.site_url)
        return site_context.get('title', 'Compania Noastră') if site_context else 'Compania Noastră'
    
    def format_services(self, services):
        if not services:
            return "• Consultanță tehnică și evaluare\n• Soluții personalizate"
        return '\n'.join([f"• {service}" for service in services])
    
    def get_recommended_config(self, requirements):
        # Logică pentru configurarea recomandată
        return "Configurație standard optimizată pentru cerințele dvs."
    
    def estimate_duration(self, requirements):
        # Estimare durată bazată pe cerințe
        size = requirements.get('size', 'medium')
        durations = {'small': '1-2 săptămâni', 'medium': '2-4 săptămâni', 'large': '1-3 luni'}
        return durations.get(size, '2-4 săptămâni')
    
    def get_recommended_actions(self, score):
        if score >= 80:
            return ["Contactează imediat", "Programează întâlnire", "Pregătește ofertă detaliată"]
        elif score >= 60:
            return ["Contactează în 24h", "Trimite materiale informative", "Programează demo"]
        elif score >= 40:
            return ["Follow-up în 3 zile", "Trimite newsletter", "Monitorizează interesul"]
        else:
            return ["Adaugă în lista de nurturing", "Follow-up lunar", "Oferă conținut educativ"]
    
    # Metode de salvare
    def save_quote(self, quote):
        try:
            collection = self.mongodb.db['quotes']
            collection.insert_one(quote)
        except Exception as e:
            print(f"Eroare salvare ofertă: {e}")
    
    def save_appointment(self, meeting):
        try:
            collection = self.mongodb.db['appointments'] 
            collection.insert_one(meeting)
        except Exception as e:
            print(f"Eroare salvare programare: {e}")
    
    def save_proposal(self, proposal):
        try:
            collection = self.mongodb.db['proposals']
            collection.insert_one(proposal)
        except Exception as e:
            print(f"Eroare salvare propunere: {e}")
    
    def save_lead_qualification(self, qualification):
        try:
            collection = self.mongodb.db['lead_qualifications']
            collection.insert_one(qualification)
        except Exception as e:
            print(f"Eroare salvare calificare lead: {e}")
