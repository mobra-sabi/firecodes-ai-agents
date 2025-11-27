import boto3
import json
import base64
import logging

logger = logging.getLogger("LambdaScraper")

class LambdaScraper:
    def __init__(self, region='us-east-1', function_name='RoScraperWorker'):
        self.client = boto3.client('lambda', region_name=region)
        self.function_name = function_name

    def fetch_page_sync(self, url):
        """Synchronous blocking call to AWS Lambda"""
        try:
            payload = {'url': url}
            
            response = self.client.invoke(
                FunctionName=self.function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            response_payload = json.loads(response['Payload'].read())
            
            if 'FunctionError' in response:
                 logger.error(f"Lambda Error: {response_payload}")
                 return None
                 
            body = json.loads(response_payload['body'])
            
            if response_payload['statusCode'] != 200:
                logger.warning(f"Lambda HTTP Error {response_payload['statusCode']}: {body.get('error')}")
                return None
                
            content_b64 = body.get('content_b64')
            if content_b64:
                return base64.b64decode(content_b64).decode('utf-8', errors='ignore')
                
            return None
            
        except Exception as e:
            logger.error(f"Error invoking Lambda for {url}: {e}")
            return None

    async def fetch_page(self, url):
        """Async wrapper (not used if called via executor)"""
        # This is just for interface compatibility if needed directly
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.fetch_page_sync, url)
