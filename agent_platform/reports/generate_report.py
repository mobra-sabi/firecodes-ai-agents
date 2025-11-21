#!/usr/bin/env python3
"""
Script CLI pentru generare rapoarte CEO Workflow
Usage: python generate_report.py <log_file> [--output-dir <dir>]
"""

import sys
import argparse
from pathlib import Path

# Add reports to path
sys.path.insert(0, str(Path(__file__).parent))
from generator.report_generator import ReportGenerator


def main():
    parser = argparse.ArgumentParser(description="Generează raport CEO Workflow din log")
    parser.add_argument("log_file", help="Calea către fișierul de log")
    parser.add_argument("--output-dir", "-o", default="output", 
                       help="Directorul de output (default: output)")
    
    args = parser.parse_args()
    
    log_file = Path(args.log_file)
    if not log_file.exists():
        print(f"❌ Eroare: Fișierul {log_file} nu există!")
        sys.exit(1)
    
    output_dir = Path(__file__).parent / args.output_dir
    
    print(f"📊 Generare raport din: {log_file}")
    print(f"📁 Output directory: {output_dir}")
    print()
    
    try:
        generator = ReportGenerator(str(log_file), str(output_dir))
        results = generator.generate_all()
        
        print("✅ Raport generat cu succes!")
        print()
        print("📄 Fișiere generate:")
        print(f"   📝 Markdown: {results.get('markdown')}")
        print(f"   📦 JSON:     {results.get('json')}")
        if results.get('graph'):
            print(f"   🎨 Graph:    {results.get('graph')}")
        print()
        print("💡 Pentru PDF: python utils/pdf_export.py <markdown_file>")
        
    except Exception as e:
        print(f"❌ Eroare la generare raport: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

