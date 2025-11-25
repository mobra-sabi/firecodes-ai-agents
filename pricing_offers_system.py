"""
Sistem de Management Oferte de Preț
===================================
Permite clienților să:
- Creeze oferte de la zero cu ajutor AI
- Importe oferte existente (PDF, Word, Excel)
- Genereze oferte noi bazate pe istoric
- Folosească template-uri personalizabile
- Exporte oferte profesionale în PDF
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from bson import ObjectId
from pymongo import MongoClient
import os
import json
import re
from openai import OpenAI

# MongoDB connection
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
client = MongoClient(MONGO_URI)
db = client["ai_agents_db"]

# Collections
offers_collection = db["pricing_offers"]
templates_collection = db["offer_templates"]
offer_items_catalog = db["offer_items_catalog"]
client_spaces_collection = db["client_spaces"]


class PricingOffersSystem:
    """Sistem complet pentru management oferte de preț"""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.llm_client = self._init_llm()
        self._ensure_client_space()
    
    def _init_llm(self):
        """Inițializează clientul LLM pentru generare oferte"""
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        if api_key:
            return OpenAI(api_key=api_key, base_url=base_url)
        return None
    
    def _ensure_client_space(self):
        """Asigură că clientul are spațiu dedicat"""
        existing = client_spaces_collection.find_one({"client_id": self.client_id})
        if not existing:
            client_spaces_collection.insert_one({
                "client_id": self.client_id,
                "created_at": datetime.now(timezone.utc),
                "settings": {
                    "company_name": "",
                    "company_address": "",
                    "company_phone": "",
                    "company_email": "",
                    "company_logo": "",
                    "default_currency": "RON",
                    "default_vat_rate": 19,
                    "payment_terms": "30 zile",
                    "bank_details": ""
                },
                "statistics": {
                    "total_offers": 0,
                    "total_value": 0,
                    "accepted_offers": 0,
                    "pending_offers": 0
                }
            })
    
    # ==================== CRUD OFERTE ====================
    
    def create_offer(self, offer_data: Dict) -> str:
        """Creează o ofertă nouă"""
        offer = {
            "client_id": self.client_id,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "status": "draft",  # draft, sent, accepted, rejected, expired
            
            # Informații client destinatar
            "recipient": {
                "name": offer_data.get("recipient_name", ""),
                "company": offer_data.get("recipient_company", ""),
                "email": offer_data.get("recipient_email", ""),
                "phone": offer_data.get("recipient_phone", ""),
                "address": offer_data.get("recipient_address", "")
            },
            
            # Detalii ofertă
            "title": offer_data.get("title", "Ofertă de preț"),
            "description": offer_data.get("description", ""),
            "reference_number": self._generate_reference_number(),
            "valid_until": offer_data.get("valid_until"),
            
            # Articole/Servicii
            "items": offer_data.get("items", []),
            # Fiecare item: {name, description, quantity, unit, unit_price, discount, vat_rate, total}
            
            # Calcule
            "subtotal": 0,
            "discount_total": 0,
            "vat_total": 0,
            "total": 0,
            "currency": offer_data.get("currency", "RON"),
            
            # Termeni și condiții
            "payment_terms": offer_data.get("payment_terms", ""),
            "delivery_terms": offer_data.get("delivery_terms", ""),
            "warranty_terms": offer_data.get("warranty_terms", ""),
            "notes": offer_data.get("notes", ""),
            
            # Metadata
            "tags": offer_data.get("tags", []),
            "category": offer_data.get("category", "general"),
            "source": offer_data.get("source", "manual"),  # manual, ai_generated, imported, template
            "template_id": offer_data.get("template_id"),
            "parent_offer_id": offer_data.get("parent_offer_id"),  # dacă e bazată pe altă ofertă
        }
        
        # Calculează totalurile
        offer = self._calculate_totals(offer)
        
        result = offers_collection.insert_one(offer)
        
        # Actualizează statisticile clientului
        self._update_client_statistics()
        
        return str(result.inserted_id)
    
    def get_offer(self, offer_id: str) -> Optional[Dict]:
        """Obține o ofertă după ID"""
        offer = offers_collection.find_one({
            "_id": ObjectId(offer_id),
            "client_id": self.client_id
        })
        if offer:
            offer["_id"] = str(offer["_id"])
        return offer
    
    def update_offer(self, offer_id: str, updates: Dict) -> bool:
        """Actualizează o ofertă"""
        updates["updated_at"] = datetime.now(timezone.utc)
        
        # Recalculează totalurile dacă s-au modificat articolele
        if "items" in updates:
            offer = self.get_offer(offer_id)
            if offer:
                offer.update(updates)
                offer = self._calculate_totals(offer)
                updates["subtotal"] = offer["subtotal"]
                updates["discount_total"] = offer["discount_total"]
                updates["vat_total"] = offer["vat_total"]
                updates["total"] = offer["total"]
        
        result = offers_collection.update_one(
            {"_id": ObjectId(offer_id), "client_id": self.client_id},
            {"$set": updates}
        )
        return result.modified_count > 0
    
    def delete_offer(self, offer_id: str) -> bool:
        """Șterge o ofertă"""
        result = offers_collection.delete_one({
            "_id": ObjectId(offer_id),
            "client_id": self.client_id
        })
        if result.deleted_count > 0:
            self._update_client_statistics()
            return True
        return False
    
    def list_offers(self, filters: Dict = None, page: int = 1, limit: int = 20) -> Dict:
        """Listează ofertele cu filtrare și paginare"""
        query = {"client_id": self.client_id}
        
        if filters:
            if filters.get("status"):
                query["status"] = filters["status"]
            if filters.get("category"):
                query["category"] = filters["category"]
            if filters.get("search"):
                query["$or"] = [
                    {"title": {"$regex": filters["search"], "$options": "i"}},
                    {"recipient.name": {"$regex": filters["search"], "$options": "i"}},
                    {"recipient.company": {"$regex": filters["search"], "$options": "i"}},
                    {"reference_number": {"$regex": filters["search"], "$options": "i"}}
                ]
            if filters.get("date_from"):
                query["created_at"] = {"$gte": filters["date_from"]}
            if filters.get("date_to"):
                if "created_at" in query:
                    query["created_at"]["$lte"] = filters["date_to"]
                else:
                    query["created_at"] = {"$lte": filters["date_to"]}
        
        total = offers_collection.count_documents(query)
        skip = (page - 1) * limit
        
        offers = list(offers_collection.find(query)
                     .sort("created_at", -1)
                     .skip(skip)
                     .limit(limit))
        
        for offer in offers:
            offer["_id"] = str(offer["_id"])
        
        return {
            "offers": offers,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
    
    def duplicate_offer(self, offer_id: str, modifications: Dict = None) -> str:
        """Duplică o ofertă existentă"""
        original = self.get_offer(offer_id)
        if not original:
            raise ValueError("Oferta nu există")
        
        # Pregătește noua ofertă
        new_offer = {
            "recipient_name": original["recipient"]["name"],
            "recipient_company": original["recipient"]["company"],
            "recipient_email": original["recipient"]["email"],
            "recipient_phone": original["recipient"]["phone"],
            "recipient_address": original["recipient"]["address"],
            "title": f"Copie - {original['title']}",
            "description": original["description"],
            "items": original["items"],
            "currency": original["currency"],
            "payment_terms": original["payment_terms"],
            "delivery_terms": original["delivery_terms"],
            "warranty_terms": original["warranty_terms"],
            "notes": original["notes"],
            "tags": original["tags"],
            "category": original["category"],
            "source": "duplicated",
            "parent_offer_id": offer_id
        }
        
        # Aplică modificările
        if modifications:
            new_offer.update(modifications)
        
        return self.create_offer(new_offer)
    
    # ==================== GENERARE AI ====================
    
    def generate_offer_from_description(self, description: str, context: Dict = None) -> Dict:
        """Generează o ofertă completă din descriere text"""
        if not self.llm_client:
            raise ValueError("LLM client not configured")
        
        # Obține istoricul ofertelor pentru context
        recent_offers = list(offers_collection.find(
            {"client_id": self.client_id}
        ).sort("created_at", -1).limit(5))
        
        # Obține catalogul de articole
        catalog_items = list(offer_items_catalog.find(
            {"client_id": self.client_id}
        ).limit(50))
        
        prompt = f"""Ești un expert în crearea ofertelor de preț pentru servicii și produse.
        
Bazându-te pe descrierea următoare, generează o ofertă de preț completă și profesională.

DESCRIERE CERINȚĂ:
{description}

CONTEXT ADIȚIONAL:
{json.dumps(context, ensure_ascii=False) if context else "Niciun context suplimentar"}

CATALOG ARTICOLE DISPONIBILE (prețuri de referință):
{json.dumps([{"name": i.get("name"), "unit_price": i.get("unit_price"), "unit": i.get("unit")} for i in catalog_items], ensure_ascii=False) if catalog_items else "Catalog gol - estimează prețuri rezonabile"}

OFERTE ANTERIOARE SIMILARE (pentru referință prețuri):
{json.dumps([{"title": o.get("title"), "total": o.get("total"), "items_count": len(o.get("items", []))} for o in recent_offers], ensure_ascii=False) if recent_offers else "Nicio ofertă anterioară"}

Generează un JSON valid cu următoarea structură:
{{
    "title": "Titlu descriptiv al ofertei",
    "description": "Descriere detaliată a serviciilor/produselor oferite",
    "recipient_name": "Numele clientului (dacă e menționat)",
    "recipient_company": "Compania clientului (dacă e menționată)",
    "items": [
        {{
            "name": "Numele serviciului/produsului",
            "description": "Descriere detaliată",
            "quantity": 1,
            "unit": "buc/mp/ora/zi/etc",
            "unit_price": 100.00,
            "discount": 0,
            "vat_rate": 19
        }}
    ],
    "payment_terms": "Termeni de plată sugerați",
    "delivery_terms": "Termeni de livrare/execuție",
    "warranty_terms": "Garanție oferită",
    "notes": "Note adiționale",
    "valid_days": 30,
    "category": "categoria serviciului"
}}

IMPORTANT:
- Prețurile să fie realiste pentru piața din România
- Include toate serviciile/produsele menționate
- Adaugă și servicii conexe dacă sunt relevante
- Folosește unități de măsură corecte
- TVA standard 19% pentru România

Răspunde DOAR cu JSON-ul, fără explicații suplimentare."""

        try:
            response = self.llm_client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            
            # Extrage JSON din răspuns
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                offer_data = json.loads(json_match.group())
                offer_data["source"] = "ai_generated"
                return offer_data
            
            raise ValueError("Nu s-a putut genera oferta")
            
        except Exception as e:
            raise ValueError(f"Eroare la generare ofertă: {str(e)}")
    
    def improve_offer_with_ai(self, offer_id: str, instructions: str = None) -> Dict:
        """Îmbunătățește o ofertă existentă cu AI"""
        offer = self.get_offer(offer_id)
        if not offer:
            raise ValueError("Oferta nu există")
        
        prompt = f"""Analizează și îmbunătățește următoarea ofertă de preț:

OFERTA CURENTĂ:
{json.dumps(offer, ensure_ascii=False, default=str)}

INSTRUCȚIUNI SPECIFICE:
{instructions if instructions else "Îmbunătățește oferta pentru a fi mai convingătoare și profesională"}

Sugerează:
1. Îmbunătățiri la descrieri
2. Ajustări de prețuri (dacă e cazul)
3. Servicii adiționale relevante
4. Formulări mai profesionale
5. Termeni mai avantajoși

Răspunde cu un JSON care conține modificările sugerate:
{{
    "suggestions": [
        {{"field": "title", "current": "...", "suggested": "...", "reason": "..."}},
        ...
    ],
    "new_items_suggested": [
        {{"name": "...", "description": "...", "unit_price": ..., "reason": "..."}}
    ],
    "pricing_analysis": "Analiza prețurilor comparativ cu piața",
    "overall_score": 85,
    "improvement_areas": ["..."]
}}"""

        try:
            response = self.llm_client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
            
            return {"error": "Nu s-au putut genera sugestii"}
            
        except Exception as e:
            return {"error": str(e)}
    
    def generate_similar_offer(self, offer_id: str, adjustments: Dict = None) -> str:
        """Generează o ofertă similară bazată pe una existentă"""
        original = self.get_offer(offer_id)
        if not original:
            raise ValueError("Oferta nu există")
        
        # Descriere pentru AI
        description = f"""
        Creează o ofertă similară cu:
        - Titlu original: {original['title']}
        - Servicii: {', '.join([i['name'] for i in original.get('items', [])])}
        - Valoare totală: {original['total']} {original['currency']}
        
        Ajustări cerute: {json.dumps(adjustments, ensure_ascii=False) if adjustments else 'Nicio ajustare specifică'}
        """
        
        new_offer_data = self.generate_offer_from_description(description, {
            "base_offer": original,
            "adjustments": adjustments
        })
        
        new_offer_data["parent_offer_id"] = offer_id
        return self.create_offer(new_offer_data)
    
    # ==================== IMPORT OFERTE ====================
    
    def import_from_text(self, text: str) -> str:
        """Importă o ofertă din text (copiat din PDF/Word)"""
        prompt = f"""Analizează următorul text care conține o ofertă de preț și extrage informațiile structurate:

TEXT OFERTĂ:
{text}

Extrage și returnează un JSON cu structura:
{{
    "title": "Titlul ofertei",
    "recipient_name": "Numele destinatarului",
    "recipient_company": "Compania destinatarului",
    "items": [
        {{
            "name": "Numele serviciului/produsului",
            "description": "Descriere",
            "quantity": 1,
            "unit": "buc",
            "unit_price": 100.00,
            "vat_rate": 19
        }}
    ],
    "subtotal": 0,
    "vat_total": 0,
    "total": 0,
    "currency": "RON",
    "payment_terms": "Termeni de plată",
    "notes": "Note extrase"
}}

Răspunde DOAR cu JSON-ul."""

        try:
            response = self.llm_client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                offer_data = json.loads(json_match.group())
                offer_data["source"] = "imported"
                return self.create_offer(offer_data)
            
            raise ValueError("Nu s-a putut parsa oferta")
            
        except Exception as e:
            raise ValueError(f"Eroare la import: {str(e)}")
    
    # ==================== TEMPLATES ====================
    
    def create_template(self, template_data: Dict) -> str:
        """Creează un template de ofertă"""
        template = {
            "client_id": self.client_id,
            "created_at": datetime.now(timezone.utc),
            "name": template_data.get("name", "Template nou"),
            "description": template_data.get("description", ""),
            "category": template_data.get("category", "general"),
            "default_items": template_data.get("items", []),
            "default_terms": {
                "payment": template_data.get("payment_terms", ""),
                "delivery": template_data.get("delivery_terms", ""),
                "warranty": template_data.get("warranty_terms", "")
            },
            "default_notes": template_data.get("notes", ""),
            "is_active": True,
            "usage_count": 0
        }
        
        result = templates_collection.insert_one(template)
        return str(result.inserted_id)
    
    def list_templates(self) -> List[Dict]:
        """Listează template-urile disponibile"""
        templates = list(templates_collection.find({
            "client_id": self.client_id,
            "is_active": True
        }).sort("usage_count", -1))
        
        for t in templates:
            t["_id"] = str(t["_id"])
        
        return templates
    
    def create_offer_from_template(self, template_id: str, customizations: Dict = None) -> str:
        """Creează o ofertă din template"""
        template = templates_collection.find_one({
            "_id": ObjectId(template_id),
            "client_id": self.client_id
        })
        
        if not template:
            raise ValueError("Template-ul nu există")
        
        offer_data = {
            "title": customizations.get("title", template["name"]),
            "description": template.get("description", ""),
            "items": template.get("default_items", []),
            "payment_terms": template["default_terms"].get("payment", ""),
            "delivery_terms": template["default_terms"].get("delivery", ""),
            "warranty_terms": template["default_terms"].get("warranty", ""),
            "notes": template.get("default_notes", ""),
            "category": template.get("category", "general"),
            "source": "template",
            "template_id": template_id
        }
        
        # Aplică customizările
        if customizations:
            if customizations.get("recipient_name"):
                offer_data["recipient_name"] = customizations["recipient_name"]
            if customizations.get("recipient_company"):
                offer_data["recipient_company"] = customizations["recipient_company"]
            if customizations.get("items"):
                offer_data["items"] = customizations["items"]
        
        # Incrementează usage count
        templates_collection.update_one(
            {"_id": ObjectId(template_id)},
            {"$inc": {"usage_count": 1}}
        )
        
        return self.create_offer(offer_data)
    
    # ==================== CATALOG ARTICOLE ====================
    
    def add_catalog_item(self, item_data: Dict) -> str:
        """Adaugă un articol în catalog"""
        item = {
            "client_id": self.client_id,
            "created_at": datetime.now(timezone.utc),
            "name": item_data.get("name", ""),
            "description": item_data.get("description", ""),
            "category": item_data.get("category", "general"),
            "unit": item_data.get("unit", "buc"),
            "unit_price": item_data.get("unit_price", 0),
            "vat_rate": item_data.get("vat_rate", 19),
            "is_active": True,
            "usage_count": 0
        }
        
        result = offer_items_catalog.insert_one(item)
        return str(result.inserted_id)
    
    def list_catalog_items(self, category: str = None) -> List[Dict]:
        """Listează articolele din catalog"""
        query = {"client_id": self.client_id, "is_active": True}
        if category:
            query["category"] = category
        
        items = list(offer_items_catalog.find(query).sort("usage_count", -1))
        for item in items:
            item["_id"] = str(item["_id"])
        
        return items
    
    # ==================== HELPER METHODS ====================
    
    def _generate_reference_number(self) -> str:
        """Generează număr de referință unic"""
        count = offers_collection.count_documents({"client_id": self.client_id})
        date_part = datetime.now().strftime("%Y%m")
        return f"OF-{date_part}-{count + 1:04d}"
    
    def _calculate_totals(self, offer: Dict) -> Dict:
        """Calculează totalurile ofertei"""
        subtotal = 0
        discount_total = 0
        vat_total = 0
        
        for item in offer.get("items", []):
            quantity = float(item.get("quantity", 1))
            unit_price = float(item.get("unit_price", 0))
            discount = float(item.get("discount", 0))
            vat_rate = float(item.get("vat_rate", 19))
            
            item_subtotal = quantity * unit_price
            item_discount = item_subtotal * (discount / 100)
            item_after_discount = item_subtotal - item_discount
            item_vat = item_after_discount * (vat_rate / 100)
            item_total = item_after_discount + item_vat
            
            item["subtotal"] = round(item_subtotal, 2)
            item["total"] = round(item_total, 2)
            
            subtotal += item_subtotal
            discount_total += item_discount
            vat_total += item_vat
        
        offer["subtotal"] = round(subtotal, 2)
        offer["discount_total"] = round(discount_total, 2)
        offer["vat_total"] = round(vat_total, 2)
        offer["total"] = round(subtotal - discount_total + vat_total, 2)
        
        return offer
    
    def _update_client_statistics(self):
        """Actualizează statisticile clientului"""
        pipeline = [
            {"$match": {"client_id": self.client_id}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "total_value": {"$sum": "$total"}
            }}
        ]
        
        stats = list(offers_collection.aggregate(pipeline))
        
        total_offers = sum(s["count"] for s in stats)
        total_value = sum(s["total_value"] for s in stats)
        accepted = next((s["count"] for s in stats if s["_id"] == "accepted"), 0)
        pending = next((s["count"] for s in stats if s["_id"] in ["draft", "sent"]), 0)
        
        client_spaces_collection.update_one(
            {"client_id": self.client_id},
            {"$set": {
                "statistics.total_offers": total_offers,
                "statistics.total_value": total_value,
                "statistics.accepted_offers": accepted,
                "statistics.pending_offers": pending
            }}
        )
    
    def get_client_space(self) -> Dict:
        """Obține spațiul clientului"""
        space = client_spaces_collection.find_one({"client_id": self.client_id})
        if space:
            space["_id"] = str(space["_id"])
        return space
    
    def update_client_settings(self, settings: Dict) -> bool:
        """Actualizează setările clientului"""
        result = client_spaces_collection.update_one(
            {"client_id": self.client_id},
            {"$set": {"settings": settings}}
        )
        return result.modified_count > 0


# ==================== EXPORT PDF ====================

class OfferPDFGenerator:
    """Generator PDF pentru oferte"""
    
    @staticmethod
    def generate_html(offer: Dict, client_settings: Dict) -> str:
        """Generează HTML pentru ofertă (pentru conversie în PDF)"""
        items_html = ""
        for i, item in enumerate(offer.get("items", []), 1):
            items_html += f"""
            <tr>
                <td>{i}</td>
                <td>
                    <strong>{item.get('name', '')}</strong>
                    <br><small>{item.get('description', '')}</small>
                </td>
                <td class="text-center">{item.get('quantity', 1)} {item.get('unit', 'buc')}</td>
                <td class="text-right">{item.get('unit_price', 0):,.2f}</td>
                <td class="text-right">{item.get('discount', 0)}%</td>
                <td class="text-right">{item.get('vat_rate', 19)}%</td>
                <td class="text-right"><strong>{item.get('total', 0):,.2f}</strong></td>
            </tr>
            """
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Ofertă {offer.get('reference_number', '')}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #333; }}
        .header {{ display: flex; justify-content: space-between; margin-bottom: 40px; }}
        .company-info {{ max-width: 300px; }}
        .company-name {{ font-size: 24px; font-weight: bold; color: #2563eb; }}
        .offer-info {{ text-align: right; }}
        .offer-number {{ font-size: 20px; font-weight: bold; }}
        .recipient {{ background: #f8fafc; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
        .recipient h3 {{ margin-top: 0; color: #64748b; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
        th {{ background: #2563eb; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 12px; border-bottom: 1px solid #e2e8f0; }}
        .text-right {{ text-align: right; }}
        .text-center {{ text-align: center; }}
        .totals {{ float: right; width: 300px; }}
        .totals table {{ margin-bottom: 0; }}
        .totals td {{ border: none; padding: 8px; }}
        .total-row {{ font-size: 18px; font-weight: bold; background: #f1f5f9; }}
        .terms {{ clear: both; margin-top: 40px; padding-top: 20px; border-top: 2px solid #e2e8f0; }}
        .terms h4 {{ color: #64748b; margin-bottom: 5px; }}
        .footer {{ margin-top: 40px; text-align: center; color: #94a3b8; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="company-info">
            <div class="company-name">{client_settings.get('company_name', 'Compania Dvs.')}</div>
            <p>{client_settings.get('company_address', '')}</p>
            <p>Tel: {client_settings.get('company_phone', '')} | Email: {client_settings.get('company_email', '')}</p>
        </div>
        <div class="offer-info">
            <div class="offer-number">OFERTĂ DE PREȚ</div>
            <p><strong>Nr:</strong> {offer.get('reference_number', '')}</p>
            <p><strong>Data:</strong> {offer.get('created_at', datetime.now()).strftime('%d.%m.%Y') if isinstance(offer.get('created_at'), datetime) else ''}</p>
            <p><strong>Valabilă până:</strong> {offer.get('valid_until', 'N/A')}</p>
        </div>
    </div>
    
    <div class="recipient">
        <h3>DESTINATAR</h3>
        <strong>{offer.get('recipient', {}).get('company', offer.get('recipient', {}).get('name', ''))}</strong>
        <p>{offer.get('recipient', {}).get('name', '')}</p>
        <p>{offer.get('recipient', {}).get('address', '')}</p>
        <p>Email: {offer.get('recipient', {}).get('email', '')} | Tel: {offer.get('recipient', {}).get('phone', '')}</p>
    </div>
    
    <h2>{offer.get('title', 'Ofertă de preț')}</h2>
    <p>{offer.get('description', '')}</p>
    
    <table>
        <thead>
            <tr>
                <th style="width: 40px;">Nr.</th>
                <th>Descriere</th>
                <th style="width: 100px;" class="text-center">Cantitate</th>
                <th style="width: 100px;" class="text-right">Preț unitar</th>
                <th style="width: 80px;" class="text-right">Discount</th>
                <th style="width: 60px;" class="text-right">TVA</th>
                <th style="width: 120px;" class="text-right">Total</th>
            </tr>
        </thead>
        <tbody>
            {items_html}
        </tbody>
    </table>
    
    <div class="totals">
        <table>
            <tr>
                <td>Subtotal:</td>
                <td class="text-right">{offer.get('subtotal', 0):,.2f} {offer.get('currency', 'RON')}</td>
            </tr>
            <tr>
                <td>Discount:</td>
                <td class="text-right">-{offer.get('discount_total', 0):,.2f} {offer.get('currency', 'RON')}</td>
            </tr>
            <tr>
                <td>TVA:</td>
                <td class="text-right">{offer.get('vat_total', 0):,.2f} {offer.get('currency', 'RON')}</td>
            </tr>
            <tr class="total-row">
                <td>TOTAL:</td>
                <td class="text-right">{offer.get('total', 0):,.2f} {offer.get('currency', 'RON')}</td>
            </tr>
        </table>
    </div>
    
    <div class="terms">
        <h4>Termeni de plată:</h4>
        <p>{offer.get('payment_terms', client_settings.get('payment_terms', ''))}</p>
        
        <h4>Termeni de livrare:</h4>
        <p>{offer.get('delivery_terms', '')}</p>
        
        <h4>Garanție:</h4>
        <p>{offer.get('warranty_terms', '')}</p>
        
        <h4>Note:</h4>
        <p>{offer.get('notes', '')}</p>
    </div>
    
    <div class="footer">
        <p>{client_settings.get('bank_details', '')}</p>
        <p>Această ofertă a fost generată automat și este valabilă fără semnătură.</p>
    </div>
</body>
</html>
        """
        
        return html

