import sys

new_code = '''    elif action == "start_briefing_trigger" or action == "start_briefing":
        # Activează modul Briefing în Controller
        controller.briefing_mode = True
        controller.briefing_step = 0
        controller.client_data = {}
        return {
            "status": "completed", 
            "message": "Briefing strategic activat. DeepSeek preia controlul. Te rog să răspunzi la întrebarea de mai jos."
        }
'''

with open("agent_api.py", "r") as f:
    content = f.read()

old_code_start = 'elif action == "start_briefing_trigger":'
old_code_end = 'return {\n            "status": "completed", \n            "message": "Briefing strategic activat. DeepSeek preia controlul."\n        }'

if old_code_start in content:
    # Simple replace since the block is unique enough
    # Need to be careful with exact whitespace in old_code_end
    
    # Let's try a more robust replace by finding start and the next elif or return
    parts = content.split(old_code_start)
    pre = parts[0]
    rest = parts[1]
    
    # The block ends before the final error return or next elif
    # In the file it looks like:
    #     elif action == "start_briefing_trigger":
    #         ...
    #         }
    #     
    #     return {"status": "error", "message": "Acțiune necunoscută"}
    
    # So we look for the closing brace of the return dict
    
    # Actually, let's just replace the known string if we can match it exactly.
    # The indentation is 4 spaces.
    
    target_str = '''    elif action == "start_briefing_trigger":
        # Activează modul Briefing în Controller
        controller.briefing_mode = True
        controller.briefing_step = 0
        controller.client_data = {}
        return {
            "status": "completed", 
            "message": "Briefing strategic activat. DeepSeek preia controlul."
        }'''
        
    if target_str in content:
        new_content = content.replace(target_str, new_code.strip('\n'))
        with open("agent_api.py", "w") as f:
            f.write(new_content)
        print("API updated successfully")
    else:
        # Fallback: try to find with flexible whitespace or manually locate
        print("Could not find exact match, trying manual location")
        # ... implementation detail ...
        # For now, let's just print failure to see.
        pass
else:
    print("Could not find start of block")

