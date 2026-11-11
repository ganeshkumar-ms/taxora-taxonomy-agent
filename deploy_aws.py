import io
import json
import mimetypes
import os
import time
import zipfile
from pathlib import Path

import boto3
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / 'backend' / '.env')

REGION = 'us-east-1'
sts = boto3.client('sts', region_name=REGION)
ACCOUNT_ID = sts.get_caller_identity()['Account']
BUCKET_NAME = f'taxora-ui-{ACCOUNT_ID}'
ROLE_NAME = 'taxora-backend-lambda-role'
LAMBDA_NAME = 'taxora-backend-api'
API_NAME = 'taxora-http-api'

s3 = boto3.client('s3', region_name=REGION)
iam = boto3.client('iam', region_name=REGION)
lam = boto3.client('lambda', region_name=REGION)
apigw = boto3.client('apigatewayv2', region_name=REGION)
cf = boto3.client('cloudfront', region_name=REGION)


def step1_s3_and_upload():
    print(f'1. Ensuring S3 bucket {BUCKET_NAME} exists...')
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
    except Exception:
        s3.create_bucket(Bucket=BUCKET_NAME)

    s3.put_public_access_block(
        Bucket=BUCKET_NAME,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': True,
        },
    )

    s3.put_bucket_cors(
        Bucket=BUCKET_NAME,
        CORSConfiguration={
            'CORSRules': [
                {
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET', 'PUT', 'POST', 'HEAD'],
                    'AllowedOrigins': ['*'],
                    'ExposeHeaders': ['ETag'],
                    'MaxAgeSeconds': 3600,
                }
            ]
        },
    )

    dist_dir = BASE_DIR / 'frontend' / 'dist'
    for file_path in dist_dir.rglob('*'):
        if file_path.is_file():
            rel = file_path.relative_to(dist_dir).as_posix()
            ctype, _ = mimetypes.guess_type(str(file_path))
            if file_path.suffix == '.js':
                ctype = 'application/javascript'
            elif file_path.suffix == '.css':
                ctype = 'text/css'
            elif file_path.suffix == '.html':
                ctype = 'text/html; charset=utf-8'
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=rel,
                Body=file_path.read_bytes(),
                ContentType=ctype or 'application/octet-stream',
            )
            print(f'   Uploaded s3://{BUCKET_NAME}/{rel} ({ctype})')


def step2_iam_role() -> str:
    print(f'2. Ensuring IAM Role {ROLE_NAME}...')
    trust = {
        'Version': '2012-10-17',
        'Statement': [{
            'Effect': 'Allow',
            'Principal': {'Service': 'lambda.amazonaws.com'},
            'Action': 'sts:AssumeRole',
        }],
    }
    try:
        role_arn = iam.get_role(RoleName=ROLE_NAME)['Role']['Arn']
    except iam.exceptions.NoSuchEntityException:
        role_arn = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust),
        )['Role']['Arn']
        print('   Created IAM role, waiting 10s for propagation...')
        time.sleep(10)

    policy_doc = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
                'Resource': '*',
            },
            {
                'Effect': 'Allow',
                'Action': ['bedrock:*', 'textract:*'],
                'Resource': '*',
            },
            {
                'Effect': 'Allow',
                'Action': ['s3:GetObject', 's3:PutObject', 's3:ListBucket'],
                'Resource': [f'arn:aws:s3:::{BUCKET_NAME}', f'arn:aws:s3:::{BUCKET_NAME}/*'],
            },
        ],
    }
    iam.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName='TaxoraBackendPolicy',
        PolicyDocument=json.dumps(policy_doc),
    )
    return role_arn


def step3_lambda_and_apigw(role_arn: str) -> str:
    print(f'3. Packaging & deploying Lambda {LAMBDA_NAME}...')
    buf = io.BytesIO()
    backend_dir = BASE_DIR / 'backend'
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(backend_dir / 'lambda_function.py', 'lambda_function.py')
        for sub in ('services', 'taxonomy'):
            for f in (backend_dir / sub).rglob('*'):
                if f.is_file() and '__pycache__' not in f.parts:
                    z.write(f, f.relative_to(backend_dir).as_posix())
        site_pkgs = backend_dir / 'venv' / 'Lib' / 'site-packages'
        if site_pkgs.exists():
            for pkg in ('pdfminer', 'charset_normalizer'):
                pkg_dir = site_pkgs / pkg
                if pkg_dir.exists():
                    for f in pkg_dir.rglob('*'):
                        if f.is_file() and '__pycache__' not in f.parts and 'cmap' not in f.parts and f.suffix != '.pyd':
                            z.write(f, f.relative_to(site_pkgs).as_posix())
    zip_bytes = buf.getvalue()

    try:
        lam.get_function(FunctionName=LAMBDA_NAME)
        lam.update_function_code(FunctionName=LAMBDA_NAME, ZipFile=zip_bytes)
        waiter = lam.get_waiter('function_updated')
        waiter.wait(FunctionName=LAMBDA_NAME)
        fn_arn = lam.update_function_configuration(
            FunctionName=LAMBDA_NAME,
            Runtime='python3.11',
            Handler='lambda_function.lambda_handler',
            Timeout=90,
            MemorySize=1024,
            Environment={'Variables': {'TAXORA_S3_BUCKET': BUCKET_NAME}},
        )['FunctionArn']
    except lam.exceptions.ResourceNotFoundException:
        fn_arn = lam.create_function(
            FunctionName=LAMBDA_NAME,
            Runtime='python3.11',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_bytes},
            Timeout=90,
            MemorySize=1024,
            Environment={'Variables': {'TAXORA_S3_BUCKET': BUCKET_NAME}},
        )['FunctionArn']
        waiter = lam.get_waiter('function_active_v2')
        waiter.wait(FunctionName=LAMBDA_NAME)

    print(f'4. Ensuring API Gateway HTTP API {API_NAME}...')
    apis = apigw.get_apis()['Items']
    existing = next((a for a in apis if a['Name'] == API_NAME), None)
    if existing:
        api_id = existing['ApiId']
    else:
        res = apigw.create_api(
            Name=API_NAME,
            ProtocolType='HTTP',
            Target=fn_arn,
        )
        api_id = res['ApiId']

    try:
        lam.add_permission(
            FunctionName=LAMBDA_NAME,
            StatementId='AllowAPIGatewayInvoke',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f'arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{api_id}/*/*',
        )
    except Exception:
        pass

    api_domain = f'{api_id}.execute-api.{REGION}.amazonaws.com'
    print(f'   API Gateway domain: {api_domain}')
    return api_domain


def step4_cloudfront(api_domain: str):
    print('5. Ensuring CloudFront OAC & Distribution...')
    oac_name = f'taxora-oac-{ACCOUNT_ID}'
    oacs = cf.list_origin_access_controls().get('OriginAccessControlList', {}).get('Items', [])
    oac = next((x for x in oacs if x['Name'] == oac_name), None)
    if oac:
        oac_id = oac['Id']
    else:
        oac_id = cf.create_origin_access_control(
            OriginAccessControlConfig={
                'Name': oac_name,
                'Description': 'OAC for TAXORA S3 Frontend',
                'SigningProtocol': 'sigv4',
                'SigningBehavior': 'always',
                'OriginAccessControlOriginType': 's3',
            }
        )['OriginAccessControl']['Id']

    s3_origin_id = 'TaxoraS3Origin'
    api_origin_id = 'TaxoraApiOrigin'
    s3_domain = f'{BUCKET_NAME}.s3.{REGION}.amazonaws.com'

    dists = cf.list_distributions().get('DistributionList', {}).get('Items', [])
    existing_dist = next((d for d in dists if d.get('Comment') == 'TAXORA AI Taxonomy Expert'), None)

    dist_config = {
        'CallerReference': f'taxora-{ACCOUNT_ID}',
        'Aliases': {'Quantity': 0},
        'DefaultRootObject': 'index.html',
        'Origins': {
            'Quantity': 2,
            'Items': [
                {
                    'Id': s3_origin_id,
                    'DomainName': s3_domain,
                    'OriginPath': '',
                    'CustomHeaders': {'Quantity': 0},
                    'S3OriginConfig': {'OriginAccessIdentity': ''},
                    'OriginAccessControlId': oac_id,
                    'ConnectionAttempts': 3,
                    'ConnectionTimeout': 10,
                    'OriginShield': {'Enabled': False},
                },
                {
                    'Id': api_origin_id,
                    'DomainName': api_domain,
                    'OriginPath': '',
                    'CustomHeaders': {'Quantity': 0},
                    'CustomOriginConfig': {
                        'HTTPPort': 80,
                        'HTTPSPort': 443,
                        'OriginProtocolPolicy': 'https-only',
                        'OriginSslProtocols': {'Quantity': 1, 'Items': ['TLSv1.2']},
                        'OriginReadTimeout': 60,
                        'OriginKeepaliveTimeout': 5,
                    },
                    'ConnectionAttempts': 3,
                    'ConnectionTimeout': 10,
                    'OriginShield': {'Enabled': False},
                },
            ],
        },
        'OriginGroups': {'Quantity': 0},
        'DefaultCacheBehavior': {
            'TargetOriginId': s3_origin_id,
            'TrustedSigners': {'Enabled': False, 'Quantity': 0},
            'TrustedKeyGroups': {'Enabled': False, 'Quantity': 0},
            'ViewerProtocolPolicy': 'redirect-to-https',
            'AllowedMethods': {
                'Quantity': 2,
                'Items': ['HEAD', 'GET'],
                'CachedMethods': {'Quantity': 2, 'Items': ['HEAD', 'GET']},
            },
            'SmoothStreaming': False,
            'Compress': True,
            'LambdaFunctionAssociations': {'Quantity': 0},
            'FunctionAssociations': {'Quantity': 0},
            'FieldLevelEncryptionId': '',
            'CachePolicyId': '658327ea-f89d-4fab-a63d-7e88639e58f6',  # CachingOptimized
        },
        'CacheBehaviors': {
            'Quantity': 1,
            'Items': [
                {
                    'PathPattern': '/api/*',
                    'TargetOriginId': api_origin_id,
                    'TrustedSigners': {'Enabled': False, 'Quantity': 0},
                    'TrustedKeyGroups': {'Enabled': False, 'Quantity': 0},
                    'ViewerProtocolPolicy': 'redirect-to-https',
                    'AllowedMethods': {
                        'Quantity': 7,
                        'Items': ['GET', 'HEAD', 'OPTIONS', 'PUT', 'POST', 'PATCH', 'DELETE'],
                        'CachedMethods': {'Quantity': 2, 'Items': ['HEAD', 'GET']},
                    },
                    'SmoothStreaming': False,
                    'Compress': True,
                    'LambdaFunctionAssociations': {'Quantity': 0},
                    'FunctionAssociations': {'Quantity': 0},
                    'FieldLevelEncryptionId': '',
                    'CachePolicyId': '4135ea2d-6df8-44a3-9df3-4b5a84be39ad',  # CachingDisabled
                    'OriginRequestPolicyId': 'b689b0a8-53d0-40ab-baf2-68738e2966ac',  # AllViewerExceptHostHeader
                }
            ],
        },
        'CustomErrorResponses': {
            'Quantity': 2,
            'Items': [
                {
                    'ErrorCode': 403,
                    'ResponsePagePath': '/index.html',
                    'ResponseCode': '200',
                    'ErrorCachingMinTTL': 10,
                },
                {
                    'ErrorCode': 404,
                    'ResponsePagePath': '/index.html',
                    'ResponseCode': '200',
                    'ErrorCachingMinTTL': 10,
                },
            ],
        },
        'Comment': 'TAXORA AI Taxonomy Expert',
        'Logging': {'Enabled': False, 'IncludeCookies': False, 'Bucket': '', 'Prefix': ''},
        'PriceClass': 'PriceClass_All',
        'Enabled': True,
        'ViewerCertificate': {
            'CloudFrontDefaultCertificate': True,
            'MinimumProtocolVersion': 'TLSv1',
            'CertificateSource': 'cloudfront',
        },
        'Restrictions': {'GeoRestriction': {'RestrictionType': 'none', 'Quantity': 0}},
        'WebACLId': '',
        'HttpVersion': 'http2',
        'IsIPV6Enabled': True,
        'ContinuousDeploymentPolicyId': '',
        'Staging': False,
    }

    if existing_dist:
        dist_id = existing_dist['Id']
        dist_domain = existing_dist['DomainName']
        dist_arn = existing_dist['ARN']
        cf.create_invalidation(
            DistributionId=dist_id,
            InvalidationBatch={'Paths': {'Quantity': 1, 'Items': ['/*']}, 'CallerReference': str(time.time())},
        )
    else:
        created = cf.create_distribution(DistributionConfig=dist_config)['Distribution']
        dist_id = created['Id']
        dist_domain = created['DomainName']
        dist_arn = created['ARN']

    bucket_policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Sid': 'AllowCloudFrontServicePrincipalReadOnly',
                'Effect': 'Allow',
                'Principal': {'Service': 'cloudfront.amazonaws.com'},
                'Action': 's3:GetObject',
                'Resource': f'arn:aws:s3:::{BUCKET_NAME}/*',
                'Condition': {'StringEquals': {'AWS:SourceArn': dist_arn}},
            }
        ],
    }
    s3.put_bucket_policy(Bucket=BUCKET_NAME, Policy=json.dumps(bucket_policy))
    print(f'\n=== DEPLOYMENT COMPLETE ===')
    print(f'CloudFront Distribution ID: {dist_id}')
    print(f'CloudFront Live URL:        https://{dist_domain}')
    print(f'Backend API Gateway URL:    https://{api_domain}')


if __name__ == '__main__':
    step1_s3_and_upload()
    role_arn = step2_iam_role()
    api_domain = step3_lambda_and_apigw(role_arn)
    step4_cloudfront(api_domain)

