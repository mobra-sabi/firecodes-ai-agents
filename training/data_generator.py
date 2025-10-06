import openai
import json
from database.mongodb_handler import MongoDBHandler
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class TrainingDataGenerator:
    def __init__(self, openai_key=None):
        if not openai_key:
            # API Key integrat direct
            openai_key = "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"
        
        self.client = openai.OpenAI(api_key=openai_key)
        self.mongodb = MongoDBHandler()
        
    def generate_training_data(self, site_url, num_samples=100):
        """Generează date de antrenament cu ChatGPT"""
        context = self.mongodb.get_site_content(site_url)
        if not context:
            print("❌ Nu s-au găsit date pentru acest site în MongoDB")
            return []
            
        system_prompt = """Ești expert în generarea de date de antrenament pentru AI.

Compania: """ + context['title'] + """
Descriere: """ + context.get('description', '') + """
Servicii: """ + context['content'][:1500] + """

Generează întrebări și răspunsuri pentru un chatbot care reprezintă această companie de protecție la foc.

Tipuri de întrebări să includă:
- Întrebări despre materiale (silicat de calciu, vată bazaltică, vopsele intumescente)
- Întrebări despre aplicații (pardoseli, structuri metalice, canale desfumare)
- Întrebări despre procese (consultanță, proiectare, execuție)
- Întrebări despre certificări și standarde
- Întrebări despre costuri și oferte

Răspunsurile să fie:
- Profesionale și precise
- Specifice pentru protecția la foc
- Orientate către soluții concrete
- În română
- Maxim 100 cuvinte per răspuns

Format JSON strict - returnează doar array-ul JSON fără text suplimentar.
"""

        training_data = []
        batch_size = 5
        total_batches = (num_samples + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            remaining = min(batch_size, num_samples - start_idx)
            
            try:
                print("📊 Generez batch " + str(batch_num + 1) + "/" + str(total_batches) + " cu " + str(remaining) + " întrebări...")
                
                user_prompt = "Generează exact " + str(remaining) + " perechi întrebare-răspuns în format JSON: [{'question': 'text', 'answer': 'text'}]. Returnează doar JSON-ul."
                
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1500
                )
                
                content = response.choices[0].message.content.strip()
                print("📝 Răspuns primit, lungime: " + str(len(content)))
                
                try:
                    content = content.replace('```json', '').replace('```', '').strip()
                    start = content.find('[')
                    end = content.rfind(']') + 1
                    
                    if start != -1 and end > start:
                        json_content = content[start:end]
                        batch_data = json.loads(json_content)
                        
                        valid_data = []
                        for item in batch_data:
                            if isinstance(item, dict) and 'question' in item and 'answer' in item:
                                valid_data.append(item)
                        
                        training_data.extend(valid_data)
                        print("✅ Adăugate " + str(len(valid_data)) + " perechi valide")
                    else:
                        print("⚠️ Nu s-a putut extrage JSON din răspuns")
                        
                except json.JSONDecodeError as e:
                    print("⚠️ Eroare la parsarea JSON: " + str(e))
                
            except Exception as e:
                print("❌ Eroare la batch " + str(batch_num) + ": " + str(e))
                
        return training_data
        
    def save_training_data(self, data, filename):
        """Salvează datele în format JSONL"""
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for item in data:
                training_item = {
                    "instruction": item['question'],
                    "input": "",
                    "output": item['answer']
                }
                json.dump(training_item, f, ensure_ascii=False)
                f.write('\n')
                
        print("💾 Date salvate în " + filepath)
        return filepath
        
    def preview_data(self, data, num_examples=3):
        """Afișează exemple"""
        print("\n📋 Preview - primele " + str(num_examples) + " exemple:")
        for i, item in enumerate(data[:num_examples]):
            print("\n--- Exemplul " + str(i+1) + " ---")
            print("❓ Întrebare: " + item['question'])
            print("✅ Răspuns: " + item['answer'])
            
    def generate_more_data(self, existing_file, additional_samples):
        """Adaugă mai multe date la un fișier existent"""
        print("📈 Generez " + str(additional_samples) + " exemple suplimentare...")
        
        new_data = self.generate_training_data("https://firestopping.ro/", additional_samples)
        
        if new_data:
            # Încarcă datele existente
            existing_data = []
            try:
                with open(existing_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        existing_data.append(json.loads(line))
            except FileNotFoundError:
                print("⚠️ Fișierul nu există, creez unul nou")
            
            # Adaugă noile date
            all_data = []
            for item in existing_data:
                all_data.append({
                    'question': item['instruction'],
                    'answer': item['output']
                })
            
            all_data.extend(new_data)
            
            # Salvează totul
            self.save_training_data(all_data, existing_file.split('/')[-1])
            print("✅ Total date: " + str(len(all_data)))
