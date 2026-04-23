"""
LF2 Lambda Function performs -- 
1) It pulls a message from the SQS queue which is pushed from LF1 (contains all booking details)
2) Fetch random restaurant ids from Elastic Search Index based on Cuisine
3) Extract extra details of restaurant by querying DynamoDB using the restaurant ids
4) Formats a message to send the customer over phone number and email address
5) Sends text message to the phone number included in the SQS message, using SNS 
6) Sends email to the provided email address using Twilio's sendgrid API
7) Deletes message from the SQS Queue using the Receipt Handle
"""

import boto3
from boto3.dynamodb.conditions import Attr
import requests
import json
import os
import ast



sqs = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')

# LF2 constants
sqs_url = 'https://sqs.us-east-1.amazonaws.com/3gdrf653/DiningConciergeSQS'
max_poll = 10
es_endpoint = 'https://search-restaurants-pgfdri.us-east-1.es.amazonaws.com/'
es_index = 'restaurant'
dynamodb_table = 'yelp_restaurants'

es_username = '****'
es_password = '********'
subject = 'REVEALED: Checkout these Restaurants of your Interest!!!'
number_of_suggestions = 5


def fetch_msg_from_sqs():
    sqs_response = sqs.receive_message(QueueUrl=sqs_url, MaxNumberOfMessages=max_poll)
    return sqs_response['Messages'] if 'Messages' in sqs_response.keys() else []

def delete_msg_from_sqs(receipt_handle):
    sqs.delete_message(QueueUrl=sqs_url, ReceiptHandle=receipt_handle)
    print('Message with Receipt Handle {} deleted'.format(receipt_handle))

def send_email(msgToSend, emailAddress):
    message = Mail(from_email=from_email, to_emails=emailAddress, subject=subject, html_content=msgToSend)
    sg = SendGridAPIClient(sendgrid_api_key)
    response = sg.send(message)
    print(response.body)

def send_sms(msgToSend, phoneNumber):
    print(msgToSend, phoneNumber)
    response = sns.publish(PhoneNumber='+1{}'.format(phoneNumber),Message=msgToSend, MessageStructure='string')
    print('SNS Response-> {}'.format(response))


def query_es(cuisine):

    es_query = '{}{}/_search?q={cuisine}'.format(es_endpoint, es_index, cuisine=cuisine)
    es_data = {}

    es_response = requests.get(es_query, auth=(es_username, es_password))

    data = json.loads(es_response.content.decode('utf-8'))
    es_data = data['hits']['hits']
   
    # extracting restaurant_ids from Elastic Search Service
    restaurant_ids = []
    for res in es_data:
        restaurant_ids.append(res['_source']['Business_ID'])
      
    return restaurant_ids

def query_dynamo_db(restaurant_ids, cuisine, location, numberOfPpl, date, time):
    table = dynamodb.Table(dynamodb_table)
    
    msgToSend = ''
    msgToSend += 'Hi there!!! \n'
    msgToSend += 'Checkout these top {number_of_suggestions} restaurants suggestions for {cuisine} cuisine in {location} for {numberOfPpl} people, on {date} at {time} \n'.format(
        number_of_suggestions=number_of_suggestions,
        cuisine=cuisine, location=location, numberOfPpl=numberOfPpl, date=date, time=time)
    
    ct = 1
    for id in restaurant_ids:
        response = table.scan(FilterExpression=Attr('Business_ID').eq(id))
        item = response['Items'][0] if len(response['Items']) > 0 else None
        if response is None or item is None:
            continue
        
        msgToSend += '[Restaurant {ct}] \n'.format(ct=ct)
        name = item['Name']
        address = item['Address']
        
        msgToSend += '{name}, located at {address} \n'.format(name=name, address=address)
        
        ct += 1
        if ct == number_of_suggestions + 1:
            break

    msgToSend += '\nWe hope you will Enjoy the {cuisine} food at these restaurants !!\n\n'.format(cuisine=cuisine)
    msgToSend += 'Thanks, \nThe Dining Concierge Chatbot Team\n'
  

    return msgToSend


def send_email(recepient, message):
    SENDER = 'cspandey016@gmail.com'
    RECIPIENT = recepient
    AWS_REGION = "us-east-1"
    SUBJECT = 'Restaurant recommendation'
    
    BODY_TEXT = (message)
    CHARSET = "UTF-8"
    client = boto3.client('ses',region_name=AWS_REGION)
    
    # Try to send the email.
    try:
        #Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
            'Body': {
                'Text': {
                    'Charset': CHARSET,
                    'Data': BODY_TEXT,
                },
            },
            'Subject': {
                'Charset': CHARSET,
                'Data': SUBJECT,
            },
        },
            Source=SENDER
        )
    # Display an error if something goes wrong.	
    except Exception as e:
    # Handle the exception
        print(f"An exception occurred: {e}")
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
    


def lambda_handler(event, context):
    dic = event
    try:
    # Extract the 'body' field from the first item in 'Records'
        body_string = dic['Records'][0]['body']
        #print('Message Body-> {}'.format(msgData))
        # Attempt to parse the 'body' string as JSON
        data = json.loads(body_string)
        cuisine = data['cuisine']['value']['interpretedValue']
        location = data['location']['value']['interpretedValue']
        phoneNumber = data['phoneNumber']['value']['interpretedValue']
        emailAddress = data['emailAddress']['value']['interpretedValue']
        numberOfPpl = data['numberOfPpl']['value']['interpretedValue']
        date = data['date']['value']['interpretedValue']
        time = data['time']['value']['interpretedValue']
        # Now 'data' contains the parsed JSON object
        print(data)
        restaurant_ids = query_es(cuisine)
        print(restaurant_ids)
        msgToSend = query_dynamo_db(restaurant_ids, cuisine, location, numberOfPpl, date, time)
        print(msgToSend)
        send_email(emailAddress, msgToSend)
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}")
    except KeyError as e:
        print(f"KeyError: {e}")
    
    #print('Received {} messages from SQS'.format(len(messages)))


    return {
        'statusCode': 200,
        'body': 'Received {} messages from SQS'.format(len(msgToSend))
    }
