import json
import urllib.request
import urllib.error
import gzip
import base64
import io

def lambda_handler(event, context):
    url = event.get('url')
    
    if not url:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing URL parameter'})
        }
    
    print(f"Processing URL: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read()
            
            # Check if response is gzipped
            if response.info().get('Content-Encoding') == 'gzip':
                try:
                    buf = io.BytesIO(content)
                    f = gzip.GzipFile(fileobj=buf)
                    content = f.read()
                except:
                    pass # Maybe it wasn't really gzipped
            
            # Return as base64 to handle any encoding issues cleanly
            encoded_content = base64.b64encode(content).decode('utf-8')
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'url': url,
                    'status': response.getcode(),
                    'content_b64': encoded_content,
                    'content_length': len(content)
                })
            }
            
    except urllib.error.HTTPError as e:
        return {
            'statusCode': e.code,
            'body': json.dumps({'error': str(e), 'url': url})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e), 'url': url})
        }

