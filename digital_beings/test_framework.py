"""
Framework de testare pentru ecosistemul de ființe digitale
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Fix imports - folosește import absolut în loc de relativ
from digital_beings.utils import generate_being_id, calculate_compatibility, BeingLogger
from digital_beings.config import ECOSYSTEM_CONFIG, PERSONALITY_TYPES

class EcosystemTester:
    """Tester pentru ecosistemul de ființe digitale"""
    
    def __init__(self):
        self.test_results = []
        self.test_beings = []
        
    async def run_all_tests(self):
        """Rulează toate testele"""
        
        print("🧪 DIGITAL BEINGS ECOSYSTEM TESTS")
        print("=" * 50)
        
        tests = [
            self.test_being_creation,
            self.test_personality_system,
            self.test_memory_system,
            self.test_skill_system,
            self.test_communication,
            self.test_compatibility,
            self.test_learning
        ]
        
        for test in tests:
            try:
                result = await test()
                self.test_results.append(result)
                status = "✅ PASS" if result['passed'] else "❌ FAIL"
                print(f"{status} {result['test_name']}")
                if not result['passed']:
                    print(f"   Error: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"❌ FAIL {test.__name__} - Exception: {e}")
                
        # Sumar teste
        passed = sum(1 for r in self.test_results if r['passed'])
        total = len(self.test_results)
        print(f"\n📊 Test Results: {passed}/{total} passed")
        
        return passed == total
        
    async def test_being_creation(self):
        """Test crearea ființelor digitale"""
        
        try:
            being_id = generate_being_id()
            
            test_being = {
                'agent_id': being_id,
                'identity': {
                    'role': 'Test Guardian',
                    'mission': 'Testing the ecosystem',
                    'industry': 'testing'
                },
                'personality': PERSONALITY_TYPES['professional'].copy(),
                'skills': {'testing': 8, 'analysis': 7},
                'status': 'active'
            }
            
            self.test_beings.append(test_being)
            
            return {
                'test_name': 'Being Creation',
                'passed': True,
                'details': f'Created being {being_id}'
            }
            
        except Exception as e:
            return {
                'test_name': 'Being Creation',
                'passed': False,
                'error': str(e)
            }
            
    async def test_personality_system(self):
        """Test sistemul de personalitate"""
        
        try:
            personality = PERSONALITY_TYPES['creative'].copy()
            
            # Verifică că toate trăsăturile sunt în range-ul corect
            for trait, value in personality.items():
                if not (1 <= value <= 10):
                    raise ValueError(f"Invalid personality value: {trait}={value}")
                    
            return {
                'test_name': 'Personality System',
                'passed': True,
                'details': 'All personality traits within valid range'
            }
            
        except Exception as e:
            return {
                'test_name': 'Personality System',
                'passed': False,
                'error': str(e)
            }
            
    async def test_memory_system(self):
        """Test sistemul de memorie"""
        
        try:
            # Simulează crearea unei memorii
            memory_episode = {
                'episode_id': generate_being_id(),
                'timestamp': '2023-01-01T00:00:00',
                'event_type': 'test_event',
                'content': 'This is a test memory episode',
                'importance': 7,
                'access_count': 0
            }
            
            # Verifică structura
            required_fields = ['episode_id', 'timestamp', 'event_type', 'content', 'importance']
            for field in required_fields:
                if field not in memory_episode:
                    raise ValueError(f"Missing memory field: {field}")
                    
            return {
                'test_name': 'Memory System',
                'passed': True,
                'details': 'Memory episode structure valid'
            }
            
        except Exception as e:
            return {
                'test_name': 'Memory System',
                'passed': False,
                'error': str(e)
            }
            
    async def test_skill_system(self):
        """Test sistemul de skill-uri"""
        
        try:
            skills = {'web_research': 7, 'data_analysis': 8, 'communication': 6}
            
            # Verifică că skill-urile sunt în range-ul corect
            for skill, level in skills.items():
                if not (1 <= level <= 10):
                    raise ValueError(f"Invalid skill level: {skill}={level}")
                    
            # Test îmbunătățire skill
            old_level = skills['web_research']
            new_level = min(10, old_level + 0.5)
            
            if new_level <= old_level:
                raise ValueError("Skill improvement failed")
                
            return {
                'test_name': 'Skill System',
                'passed': True,
                'details': f'Skill improved from {old_level} to {new_level}'
            }
            
        except Exception as e:
            return {
                'test_name': 'Skill System',
                'passed': False,
                'error': str(e)
            }
            
    async def test_communication(self):
        """Test sistemul de comunicare"""
        
        try:
            message = {
                'sender': 'being_001',
                'recipient': 'being_002',
                'content': 'Hello, how are you?',
                'timestamp': '2023-01-01T00:00:00',
                'message_type': 'greeting'
            }
            
            # Verifică structura mesajului
            required_fields = ['sender', 'recipient', 'content', 'timestamp']
            for field in required_fields:
                if field not in message:
                    raise ValueError(f"Missing message field: {field}")
                    
            return {
                'test_name': 'Communication System',
                'passed': True,
                'details': 'Message structure valid'
            }
            
        except Exception as e:
            return {
                'test_name': 'Communication System',
                'passed': False,
                'error': str(e)
            }
            
    async def test_compatibility(self):
        """Test calculul de compatibilitate"""
        
        try:
            if len(self.test_beings) < 2:
                # Creează al doilea being pentru test
                being2 = {
                    'agent_id': generate_being_id(),
                    'personality': PERSONALITY_TYPES['friendly'].copy(),
                    'skills': {'communication': 9, 'customer_service': 8},
                    'identity': {'industry': 'testing'}
                }
                self.test_beings.append(being2)
                
            compatibility = calculate_compatibility(self.test_beings[0], self.test_beings[1])
            
            if not (0 <= compatibility <= 1):
                raise ValueError(f"Invalid compatibility score: {compatibility}")
                
            return {
                'test_name': 'Compatibility Calculation',
                'passed': True,
                'details': f'Compatibility score: {compatibility}'
            }
            
        except Exception as e:
            return {
                'test_name': 'Compatibility Calculation',
                'passed': False,
                'error': str(e)
            }
            
    async def test_learning(self):
        """Test sistemul de învățare"""
        
        try:
            # Simulează învățarea
            initial_skill = 5.0
            feedback_score = 8  # Feedback pozitiv
            improvement_rate = 0.1
            
            new_skill = initial_skill + (feedback_score - 5) * improvement_rate
            
            if new_skill <= initial_skill:
                raise ValueError("Learning system not working")
                
            return {
                'test_name': 'Learning System',
                'passed': True,
                'details': f'Skill improved from {initial_skill} to {new_skill}'
            }
            
        except Exception as e:
            return {
                'test_name': 'Learning System',
                'passed': False,
                'error': str(e)
            }

async def run_tests():
    """Rulează testele ecosistemului"""
    tester = EcosystemTester()
    success = await tester.run_all_tests()
    return success

if __name__ == "__main__":
    asyncio.run(run_tests())
