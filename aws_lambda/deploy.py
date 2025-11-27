import boto3
import zipfile
import io
import time
import json
import os

# Config
FUNCTION_NAME = 'RoScraperWorker'
REGION = 'us-east-1'
ROLE_NAME = 'RoScraperRole'

iam = boto3.client('iam', region_name=REGION)
lambda_client = boto3.client('lambda', region_name=REGION)

def create_role():
    """Creates IAM role for Lambda"""
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        # Check if role exists
        try:
            role = iam.get_role(RoleName=ROLE_NAME)
            print(f"✅ Role {ROLE_NAME} exists. ARN: {role['Role']['Arn']}")
            return role['Role']['Arn']
        except iam.exceptions.NoSuchEntityException:
            pass
            
        print(f"Creating role {ROLE_NAME}...")
        role = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        
        # Attach basic execution policy
        iam.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        
        print("⏳ Waiting for role propagation...")
        time.sleep(10) # AWS needs time to propagate IAM changes
        return role['Role']['Arn']
        
    except Exception as e:
        print(f"❌ Error creating role: {e}")
        raise

def deploy_function(role_arn):
    """Zips code and deploys Lambda"""
    print("📦 Zipping code...")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write('/srv/hf/ai_agents/aws_lambda/lambda_function.py', 'lambda_function.py')
    
    zip_buffer.seek(0)
    zip_content = zip_buffer.read()
    
    try:
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName=FUNCTION_NAME)
            print(f"🔄 Updating function code {FUNCTION_NAME}...")
            lambda_client.update_function_code(
                FunctionName=FUNCTION_NAME,
                ZipFile=zip_content
            )
        except lambda_client.exceptions.ResourceNotFoundException:
            print(f"🚀 Creating new function {FUNCTION_NAME}...")
            lambda_client.create_function(
                FunctionName=FUNCTION_NAME,
                Runtime='python3.12',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                Timeout=15, # 15 seconds limit per page
                MemorySize=128
            )
            
        print("✅ Deployment SUCCESS!")
        
    except Exception as e:
        print(f"❌ Error deploying function: {e}")
        raise

if __name__ == "__main__":
    try:
        arn = create_role()
        deploy_function(arn)
    except Exception as e:
        print(f"Fatal error: {e}")

