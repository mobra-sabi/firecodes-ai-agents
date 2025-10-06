import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from agents.final_agent import FinalAgent
from client_features.commercial_agent import CommercialAgent
import re
import json

class EnhancedCommercialAgent(FinalAgent):
    def __init__(self, site_url):
        super().__init__(site_url)
        self.commercial_agent = CommercialAgent(site_url)
        self.conversation_context = {}
        
    def analyze_intent(self, question):
        """Analizează intenția din întrebarea clientului"""
        
        question_lower = question.lower()
        
        # Detectare intenții comerciale
        intents = {
            'price_inquiry': ['preț', 'cost', 'tarif', 'cât costă', 'ofertă', 'buget'],
            'meeting_request': ['întâlnire', 'programare', 'când putem', 'vizită', 'discutie'],
            'service_config': ['cum se face', 'opțiuni', 'tipuri', 'variante', 'configurare'],
            'proposal_request': ['propunere', 'ofertă detaliată', 'proiect', 'contract'],
            'qualification': ['companie', 'experiență', 'referințe', 'portofoliu', 'certificări']
        }
        
        detected_intents = []
        for intent, keywords in intents.items():
            if any(keyword in question_lower for keyword in keywords):
                detected_intents.append(intent)
                
        return detected_intents[0] if detected_intents else 'general'
        
    def extract_project_details(self, question):
        """Extrage detalii despre proiect din conversație"""
        
        details = {}
        question_lower = question.lower()
        
        # Extragere tip serviciu
        services = {
            'vopsitorii_industriale': ['vopsit', 'vopsea', 'vopsitori', 'intumescent'],
            'reparatii_industriale': ['reparare', 'reparații', 'întreținere', 'mentenanță'],
            'reabilitare_silozuri': ['siloz', 'silozuri', 'reabilitare'],
            'constructii_industriale': ['construcție', 'construire', 'edificare']
        }
        
        for service_type, keywords in services.items():
            if any(keyword in question_lower for keyword in keywords):
                details['service'] = service_type
                break
        
        # Extragere dimensiuni (folosind regex)
        area_patterns = [
            r'(\d+)\s*m[p2²]',
            r'(\d+)\s*metri',
            r'(\d+)\s*mp'
        ]
        
        for pattern in area_patterns:
            match = re.search(pattern, question_lower)
            if match:
                details['area'] = int(match.group(1))
                break
                
        # Extragere complexitate
        if any(word in question_lower for word in ['simplu', 'basic', 'standard']):
            details['complexity'] = 'simple'
        elif any(word in question_lower for word in ['complex', 'dificil', 'complicat']):
            details['complexity'] = 'complex'
        else:
            details['complexity'] = 'normal'
            
        return details
        
    def enhanced_answer(self, question):
        """Răspuns îmbunătățit cu funcționalități comerciale"""
        
        intent = self.analyze_intent(question)
        
        if intent == 'price_inquiry':
            return self.handle_price_inquiry(question)
        elif intent == 'meeting_request':
            return self.handle_meeting_request(question)
        elif intent == 'service_config':
            return self.handle_service_configuration(question)
        elif intent == 'proposal_request':
            return self.handle_proposal_request(question)
        elif intent == 'qualification':
            return self.handle_qualification_questions(question)
        else:
            return super().answer_question(question)
            
    def handle_price_inquiry(self, question):
        """Gestionează întrebările despre prețuri"""
        
        # Obține răspunsul de bază
        base_answer = super().answer_question(question)
        
        # Extrage detalii proiect
        project_details = self.extract_project_details(question)
        
        if project_details.get('service') and project_details.get('area'):
            # Calculează oferta
            quote = self.commercial_agent.calculate_quotes(project_details)
            
            if 'error' not in quote:
                price_info = f"""
                
💰 ESTIMARE PRELIMINARĂ:
📏 Suprafață: {quote['area']} mp
🔧 Serviciu: {quote['service'].replace('_', ' ').title()}
📊 Complexitate: {quote['complexity']}
💵 Preț estimat: {quote['final_price']:.2f} {quote['currency']}

⚠️ ATENȚIE: Aceasta este o estimare preliminară.
Pentru o ofertă exactă, avem nevoie de:
• Evaluare la fața locului
• Specificații tehnice detaliate
• Condițiile concrete de lucru

📞 Programați o consultanță GRATUITĂ pentru ofertă precisă!"""
                
                return base_answer + price_info
        
        # Dacă nu avem destule detalii
        details_request = """

💰 Pentru o ofertă precisă, vă rugăm să ne spuneți:
• Ce tip de serviciu necesitați?
• Câți metri pătrați/cubi sunt implicați?
• Care este locația proiectului?
• În ce interval de timp doriți execuția?

📞 Contactați-ne pentru o evaluare gratuită și ofertă personalizată!"""
        
        return base_answer + details_request
        
    def handle_meeting_request(self, question):
        """Gestionează cererile de întâlnire"""
        
        base_answer = super().answer_question(question)
        
        # Încearcă să programeze automat
        availability_info = {
            'preferred_time': 'morning' if 'dimineața' in question.lower() else 'afternoon',
            'client_info': {'source': 'chat', 'question': question}
        }
        
        meeting = self.commercial_agent.schedule_meetings(availability_info)
        
        meeting_info = f"""

📅 PROGRAMARE ÎNTÂLNIRE:

Vă propunem următoarele intervale disponibile:
{chr(10).join([f"• {slot}" for slot in meeting['suggested_slots']])}

📋 Pentru confirmarea întâlnirii, vă rugăm să ne comunicați:
• Intervalul preferat din cele propuse
• Persoana de contact
• Numărul de telefon
• Adresa unde să ne deplasăm (dacă e cazul)

📞 Confirmați prin telefon sau email disponibilitatea!
✅ Consultanța inițială este GRATUITĂ!"""
        
        return base_answer + meeting_info
        
    def handle_service_configuration(self, question):
        """Gestionează întrebările despre configurarea serviciilor"""
        
        base_answer = super().answer_question(question)
        
        project_details = self.extract_project_details(question)
        service_type = project_details.get('service', 'general')
        
        config = self.commercial_agent.configure_services({'type': service_type})
        
        if config['available_options']:
            config_info = f"""

🔧 OPȚIUNI DISPONIBILE pentru {service_type.replace('_', ' ').title()}:

{self.format_service_options(config['available_options'])}

⏱️ Durată estimată: {config['estimated_duration']}
🎯 Configurația recomandată: {config['recommended_config']}

💡 Pentru alegerea optimă, recomandăm o consultanță tehnică cu specialiștii noștri!"""
            
            return base_answer + config_info
        
        return base_answer + "\n\n🔧 Pentru detalii tehnice specifice, vă rugăm să ne contactați direct!"
        
    def handle_proposal_request(self, question):
        """Gestionează cererile de propuneri comerciale"""
        
        base_answer = super().answer_question(question)
        
        proposal_info = """

📋 PROPUNERE COMERCIALĂ PERSONALIZATĂ:

Pentru a vă pregăti o propunere detaliată, avem nevoie de:

📏 DETALII TEHNICE:
• Tipul serviciului solicitat
• Dimensiunile/suprafețele implicate
• Specificații tehnice particulare
• Standardele/certificările necesare

📅 ASPECTE ORGANIZATORICE:
• Timeline-ul dorit pentru proiect
• Bugetul aproximativ disponibil
• Persoana responsabilă cu decizia

📞 CONTACT:
• Nume companie și persoană de contact
• Telefon și email
• Adresa pentru deplasare (dacă e necesar)

✅ Propunerea va fi trimisă în maximum 48 de ore de la primirea tuturor informațiilor!"""
        
        return base_answer + proposal_info
        
    def handle_qualification_questions(self, question):
        """Gestionează întrebările despre calificările companiei"""
        
        base_answer = super().answer_question(question)
        
        # Califică lead-ul bazat pe întrebare
        client_interest = {
            'budget': self.estimate_budget_from_question(question),
            'project_size': self.estimate_project_size(question),
            'timeline': 'flexible',
            'is_decision_maker': 'experiență' in question.lower() or 'referințe' in question.lower(),
            'has_experience': 'companie' in question.lower()
        }
        
        lead_qualification = self.commercial_agent.qualify_leads(client_interest)
        
        qualification_info = f"""

🏆 DESPRE EXPERIENȚA NOASTRĂ:

✅ Peste 10 ani de experiență în domeniu
✅ Echipă de specialiști certificați
✅ Proiecte finalizate cu succes în toată țara
✅ Certificări și standarde internaționale
✅ Garanție extinsă pentru toate lucrările

📊 Lead clasificat ca: {lead_qualification['quality']}
🎯 Acțiuni recomandate: {', '.join(lead_qualification['recommended_actions'][:2])}

📁 Portofoliul complet și referințele pot fi consultate la întâlnire!"""
        
        return base_answer + qualification_info
        
    # Metode helper
    def format_service_options(self, options):
        """Formatează opțiunile de servicii"""
        formatted = []
        for key, values in options.items():
            if isinstance(values, list):
                formatted.append(f"• {key.title()}: {', '.join(values)}")
            else:
                formatted.append(f"• {key.title()}: {values}")
        return '\n'.join(formatted)
        
    def estimate_budget_from_question(self, question):
        """Estimează bugetul din întrebare"""
        if any(word in question.lower() for word in ['mare', 'important', 'complex']):
            return 50000
        elif any(word in question.lower() for word in ['mediu', 'standard']):
            return 20000
        else:
            return 5000
            
    def estimate_project_size(self, question):
        """Estimează dimensiunea proiectului"""
        if any(word in question.lower() for word in ['mare', 'complex', 'important']):
            return 'large'
        elif any(word in question.lower() for word in ['mediu', 'standard']):
            return 'medium'
        else:
            return 'small'
            
    def save_enhanced_interaction(self, question, answer, intent, details=None):
        """Salvează interacțiunea îmbunătățită"""
        interaction = {
            'site_url': self.site_url,
            'question': question,
            'answer': answer,
            'detected_intent': intent,
            'extracted_details': details,
            'timestamp': str(datetime.now()),
            'agent_type': 'enhanced_commercial'
        }
        
        try:
            collection = self.mongodb.db['enhanced_interactions']
            collection.insert_one(interaction)
        except Exception as e:
            print(f"⚠️ Eroare salvare interacțiune: {e}")
