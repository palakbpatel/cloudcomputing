import boto3
import json
import time
from decimal import Decimal
# Initialize the DynamoDB resource and specify your region

aws_access_key_id = 'AZ47U'
aws_secret_access_key = 'aAegfgfgeG3XwF'

import os
os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
dynamodb = boto3.resource('dynamodb', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key ,region_name='us-east-1')
credentials = boto3.Session().get_credentials()
print(credentials)
# Replace 'YourTable' with your DynamoDB table name
table_name = 'yelp_restaurants'
table = dynamodb.Table(table_name)

file_path = 'Restaurant_data.json'  # Replace with your file path

with open(file_path, 'r') as json_file:
    data = json.load(json_file, parse_float=Decimal)  # Parse float as Decimal

for item in data:
        table.put_item(Item=item)
        time.sleep(0.25)

print(f'Data uploaded to DynamoDB table: {table_name}')
