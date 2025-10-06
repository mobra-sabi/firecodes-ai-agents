"""
Configurația pentru ecosistemul de ființe digitale
"""

# Configurații generale
ECOSYSTEM_CONFIG = {
    'max_beings_per_ecosystem': 50,
    'memory_capacity_per_being': 10000,
    'skill_improvement_rate': 0.1,
    'interaction_timeout': 30,  # secunde
    'auto_creation_enabled': True,
    'learning_enabled': True,
    'gamification_enabled': True
}

# Tipuri de personalități disponibile
PERSONALITY_TYPES = {
    'professional': {
        'professionalism': 9,
        'creativity': 5,
        'friendliness': 6,
        'formality': 8
    },
    'creative': {
        'professionalism': 6,
        'creativity': 9,
        'friendliness': 8,
        'formality': 4
    },
    'friendly': {
        'professionalism': 7,
        'creativity': 6,
        'friendliness': 9,
        'formality': 5
    },
    'technical': {
        'professionalism': 8,
        'creativity': 7,
        'friendliness': 5,
        'formality': 7
    }
}

# Tipuri de skill-uri disponibile
AVAILABLE_SKILLS = [
    'web_research',
    'data_analysis', 
    'content_creation',
    'client_communication',
    'trend_analysis',
    'visual_analysis',
    'social_media',
    'automation',
    'strategic_thinking',
    'creative_problem_solving',
    'technical_expertise',
    'sales_optimization',
    'customer_service',
    'project_management',
    'quality_assurance'
]

# Configurații pentru comunicare
COMMUNICATION_CONFIG = {
    'max_conversation_length': 20,  # mesaje
    'message_timeout': 10,  # secunde
    'auto_response_enabled': True,
    'emotion_simulation': True,
    'memory_integration': True
}

# Configurații pentru rețea
NETWORK_CONFIG = {
    'max_connections_per_being': 10,
    'collaboration_threshold': 0.6,  # similaritate pentru colaborare
    'competition_threshold': 0.8,    # similaritate pentru competiție
    'alliance_duration': 30,         # zile
    'network_evolution': True
}

# Configurații pentru vizualizare
VISUALIZATION_CONFIG = {
    'update_interval': 5,  # secunde
    'max_nodes_display': 100,
    'animation_enabled': True,
    'real_time_updates': True,
    'export_formats': ['png', 'svg', 'pdf']
}

# Configurații pentru gamification
GAMIFICATION_CONFIG = {
    'leveling_enabled': True,
    'achievement_system': True,
    'competition_leagues': True,
    'reward_system': True,
    'leaderboards': True
}
