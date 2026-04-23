import json
from requests_aws4auth import AWS4Auth
import boto3
import requests
aws_access_key_id = 'AK7U'
aws_secret_access_key = 'aAeIOndsfdgfk/XdfgwF'
import os
os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key

dynamodb = boto3.resource('dynamodb', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key ,region_name='us-east-1')
table = dynamodb.Table('yelp_restaurants')

host = 'https://search-restaurants-pu5mxm7ts6gebt7lfzqfd32uri.us-east-1.es.amazonaws.com'
path = '/restaurants/Restaurant/'
region = 'us-east-1'
service = 'es'
credentials = boto3.Session().get_credentials()
print(credentials)
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)


def start():
    response = table.scan()
    i = 0
    url = host + path

    headers = {"Content-Type": "application/json"}

    for r in response['Items']:
        payload = {"RestaurantID": r['Business_ID'], "Cuisine": r['Cuisine']}
        res = requests.post(url, auth=("admin", "Admin@1234"), data=json.dumps(payload).encode("utf-8"), headers=headers)
        i += 1
        print(i)
        print(res.text)


if __name__ == '__main__':
    start()
