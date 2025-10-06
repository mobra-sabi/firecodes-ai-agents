import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class AIModelFactory:
    """Fabrică de modele AI custom pentru vânzare"""
    
    def __init__(self):
        self.training_pipeline = {}
        self.model_catalog = {}
        
    def custom_model_services(self):
        return {
            'domain_specific_models': {
                'price': '5000-50000 RON per model',
                'examples': [
                    'Model pentru domeniul medical românesc',
                    'Model pentru legal/juridic RO',
                    'Model pentru industria auto',
                    'Model pentru agricultură',
                    'Model pentru retail/fashion'
                ],
                'delivery_time': '1-4 săptămâni',
                'gpu_usage': '100-500 GPU pentru training'
            },
            
            'fine_tuned_solutions': {
                'price': '1000-10000 RON per model',
                'target': 'Companii care vor AI personalizat',
                'use_cases': [
                    'Chatbot cu personalitatea brandului',
                    'Content generator pentru nișă specifică',
                    'Clasificator documente companie',
                    'Sentiment analysis pentru reviews'
                ]
            },
            
            'model_hosting_service': {
                'price': '50-500 RON/lună per model',
                'features': [
                    'API endpoints pentru modelele client',
                    'Scaling automat',
                    'Monitoring și analytics',
                    'SLA garantat'
                ]
            }
        }
        
    def data_processing_services(self):
        """Servicii de procesare masivă de date"""
        return {
            'data_labeling': '0.10-1.00 RON per etichetă',
            'data_cleaning': '0.01 RON per înregistrare',
            'data_augmentation': '0.05 RON per sample generat',
            'dataset_creation': '1000-50000 RON per dataset'
        }
        
    def training_infrastructure(self):
        """Infrastructura pentru training modele custom"""
        return {
            'distributed_training': 'Training pe 100-500 GPU simultan',
            'experiment_tracking': 'MLflow pentru tracking experimente',
            'model_versioning': 'Versioning automat modele',
            'a_b_testing': 'Testing automat performanță modele',
            'deployment_pipeline': 'Deploy automat în producție'
        }
        
    def marketplace_features(self):
        """Funcționalități marketplace pentru modele"""
        return {
            'model_store': 'Magazin online pentru modele pre-trained',
            'demo_environment': 'Mediu de test pentru clienți',
            'performance_metrics': 'Metrici transparente performanță',
            'usage_analytics': 'Analytics utilizare modele',
            'revenue_sharing': 'Împărțire venituri cu dezvoltatori'
        }
        
    def enterprise_training_packages(self):
        """Pachete enterprise pentru training modele"""
        return {
            'starter_package': {
                'price': '5000 RON',
                'gpu_hours': '100 ore GPU',
                'models': '1-2 modele simple',
                'support': 'Email support'
            },
            'professional_package': {
                'price': '25000 RON',
                'gpu_hours': '500 ore GPU',
                'models': '3-5 modele complexe',
                'support': 'Suport dedicat + consultanță'
            },
            'enterprise_package': {
                'price': '100000 RON',
                'gpu_hours': '2000 ore GPU',
                'models': 'Unlimited',
                'support': 'Echipă dedicată + on-site'
            }
        }
