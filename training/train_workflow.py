#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data_generator import TrainingDataGenerator
from fine_tune_qwen import QwenFineTuner

def main():
    print("🤖 Workflow Antrenament AI Custom")
    print("=" * 50)
    
    # API Key este deja integrat în data_generator
    generator = TrainingDataGenerator()
    
    print("\n📚 Opțiuni disponibile:")
    print("1. Generează 50 date noi")
    print("2. Generează 200 date noi") 
    print("3. Adaugă date la fișier existent")
    print("4. Începe fine-tuning cu datele existente")
    
    choice = input("\nAlege opțiunea (1-4): ").strip()
    
    if choice == "1":
        print("🎯 Generez 50 perechi...")
        data = generator.generate_training_data("https://firestopping.ro/", 50)
        if data:
            generator.preview_data(data)
            file_path = generator.save_training_data(data, "firestopping_50.jsonl")
            print("✅ Date salvate în " + file_path)
            
    elif choice == "2":
        print("🎯 Generez 200 perechi...")
        data = generator.generate_training_data("https://firestopping.ro/", 200)
        if data:
            generator.preview_data(data)
            file_path = generator.save_training_data(data, "firestopping_200.jsonl")
            print("✅ Date salvate în " + file_path)
            
    elif choice == "3":
        filename = input("Nume fișier existent (ex: firestopping_50.jsonl): ")
        additional = int(input("Câte date suplimentare să generez? "))
        generator.generate_more_data(filename, additional)
        
    elif choice == "4":
        filename = input("Nume fișier cu date (ex: firestopping_200.jsonl): ")
        print("🚀 Începe fine-tuning...")
        tuner = QwenFineTuner()
        model_path = tuner.fine_tune(filename)
        print("🎉 Model antrenat salvat în: " + model_path)
        
    else:
        print("❌ Opțiune invalidă")

if __name__ == "__main__":
    main()
