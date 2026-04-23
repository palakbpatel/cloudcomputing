
"""
LF1 Lambda Function performs -- 
1) The fucntion gets triggered for the DiningSuggestionsIntent.
2) Slot values are retrived from the event object that lambda receives.
3) Validations are performed on each slot.
4) If all slot values are valid, they are sent to SQS.

"""


import boto3
import math
import dateutil.parser
import datetime
import time
import re
import os
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
sqs = boto3.client('sqs')
sqs_url = 'https://sqs.us-east-1.amazonaws.com/369g6653/DiningConciergeSQS'

min_number = 1
max_number = 15
default_cuisines = ['indpak', 'chinese', 'mexican', 'italian']

regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'


def get_slots(intent_request):
    return intent_request['sessionState']['intent']['slots']

def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'ElicitSlot',
                'slotToElicit': slot_to_elicit,
            },
            'intent': {
                'name': intent_name,
                'slots': slots
            }
        },
        'messages': [message]
    }
    
def send_slots_to_sqs(slots):
    response = sqs.send_message(
        QueueUrl=sqs_url,
        MessageBody=json.dumps(slots)
    )
    logger.info('SQS Response-> ')
    logger.info(response)
    
def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            'isValid': is_valid,
            'violatedSlot': violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }

def validate_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False
    
def dining_suggestions(intent_request):
    """
    Manages dialog and fulfillment for the DiningSuggestionsIntent.
    Beyond fulfillment, the implementation of this intent demonstrates the use of the elicitSlot dialog action
    in slot validation and re-prompting.
    """
    
    slots = get_slots(intent_request)
    
    intent_name = intent_request['sessionState']['intent']['name']
    location = slots['location']['value']['interpretedValue'] if slots['location'] is not None else None
    cuisine = slots['cuisine']['value']['interpretedValue'] if slots['cuisine'] is not None else None
    numOfPpl = slots['numberOfPpl']['value']['interpretedValue'] if slots['numberOfPpl'] is not None else None
    date = slots['date']['value']['interpretedValue'] if slots['date'] is not None else None
    time = slots['time']['value']['interpretedValue'] if slots['time'] is not None else None
    phoneNumber = slots['phoneNumber']['value']['interpretedValue'] if slots['phoneNumber'] is not None else None
    emailAddress = slots['emailAddress']['value']['originalValue'] if slots['emailAddress'] is not None else None
    source = intent_request['invocationSource']
    

    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        
        valid_result = validate_dining_suggestions(location, cuisine, numOfPpl, date, time, phoneNumber, emailAddress)
        logger.info('Validation Result -> {}'.format(valid_result['isValid']))
        if not valid_result['isValid']:
            slots[valid_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionState'].get('sessionAttributes'),
                                intent_name,
                                slots,
                                valid_result['violatedSlot'],
                                valid_result.get('message'))

        # Pass data back through session attributes to be used in various prompts defined on the bot model.
        output_session_attributes = intent_request['sessionState'].get('sessionAttributes') if intent_request['sessionState'].get('sessionAttributes') is not None else {}

        return delegate(output_session_attributes, intent_name, get_slots(intent_request))

    # Send the slot data to SQS queue
    send_slots_to_sqs(slots)

    # Send the closing response back to the user.
    logger.debug('Closing the intent as its fulfilled')
    return close(intent_request['sessionState']['sessionAttributes'],
                intent_name,
                'Fulfilled',
                {'contentType': 'PlainText',
                 'content': 'You’re all set. You will receive my suggestions shortly on {}! Happy Dining!'.format(emailAddress)})


def delegate(session_attributes, intent_name, slots):
    return {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Delegate'
            },
            'intent': {
                'name': intent_name,
                'slots': slots
            }
        }
    }

def close(session_attributes, intent_name, fulfillment_state, message):
    return {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close'
            },
            'intent': {
                'name': intent_name,
                'state': fulfillment_state
            }
        },
        'messages': [message]
    }
                                 
   
def validate_dining_suggestions(location, cuisine, numOfPpl, date, time, phoneNumber,  emailAddress):
    '''
    Function that performs validation for every slot.
    1. Location can only be Manhattan.
    2. Cuisine can belong to Thai, Chinese, Mexican, Italian, American.
    3. Number of people can be more than 2 and less than 15.
    4. Date format needs to be correct and needs to be in the future.
    5. Time format needs to be correct.
    6. Phone number should consist of 10 digits.
    7. Email address should be valid according to standard convention.
    
    '''
    if location is None:
        logger.debug('Location is None')
        return build_validation_result(False,
                                       'location',
                                       'I am sorry. At the moment I can only help with restaurants in manhattan?')
    elif location.lower() != 'manhattan'.lower():
        logger.debug('Location {} is not valid.'.format(location))
        return build_validation_result(False,
                                       'location',
                                       'I can find you a restaurant in {}, Can you please try again?'.format('Manhattan'))
    if cuisine is None:
        logger.debug('Cuisine is None')
        return build_validation_result(False,
                                       'cuisine',
                                       'Okay!, {}. Which cuisine would you want to try?'.format('Manhattan'))
    elif cuisine.lower() not in default_cuisines:
        logger.debug('Invalid Cuisine-> {}'.format(cuisine))
        return build_validation_result(False,
                                       'cuisine',
                                       'Sorry, I can\'t find restaurants for {} cuisine. I can find restaurants only for Chinese, Mexican, Italian and indpak cuisines. Could you please try cuisine in this list?'.format(cuisine))      
                                         
    logger.info('Number of People captured-> {}, Max number of people -> {}'.format(numOfPpl, max_number))
    numberOfPpl = int(numOfPpl) if numOfPpl is not None else numOfPpl

    if numberOfPpl is None:
        logger.debug('numberOfPpl is None')
        return build_validation_result(False,
                                       'numberOfPpl',
                                       'Ok, how many people will be dining together?')
                                      
    elif numberOfPpl < min_number or numberOfPpl > max_number:
        logger.debug('Invalid numberOfPpl-> {}'.format(numberOfPpl))
        return build_validation_result(False,
                                       'numberOfPpl',
                                       'Please enter between a minimum of {} and a maximum of {} people.'.format(min_number, max_number))
                                       
    date_obj = datetime.datetime.strptime(date, '%Y-%m-%d').date() if date is not None else None
    if date is None:
        logger.debug('Date is None')
        return build_validation_result(False, 'date', 'Which date do you plan to visit the restaurant?')
    else:
        if not validate_date(date):
            logger.debug('Invalid Date-> {}'.format(date))
            return build_validation_result(False, 'date', 'I did not understand that, which date do you plan to visit the restaurant?')
        elif date_obj < datetime.date.today():
            logger.debug('Date is in the past-> {}'.format(date))
            return build_validation_result(False, 'date', 'You can\'t reserve your seats in the past. Which date do you plan to visit the restaurant?')

    if time is None:
        logger.debug('Time is None')
        return build_validation_result(False, 'time', 'And at what time?')
    else:
        if len(time) != 5:
            logger.debug('Invalid Time-> {}'.format(time))
            return build_validation_result(False, 'time', 'Invalid Time format -> {}. Can you try again?'.format(time))

        hour, minute = time.split(':')
        hour = int(hour)
        minute = int(minute)
        if math.isnan(hour) or math.isnan(minute):
            logger.debug('Invalid Time-> {}'.format(time))
            return build_validation_result(False, 'time', 'Invalid Time format -> {}. Can you try again?'.format(time))

        time_obj = datetime.datetime.strptime(time, '%H:%M').time()
        combined_datetime = datetime.datetime.combine(date_obj, time_obj)
        if combined_datetime < datetime.datetime.now():
            # Time is in the past
            logger.debug('Time is in the past-> {}'.format(time))
            return build_validation_result(False, 'time', 'You can\'t reserve your seats in the past. Can you give me a time in the future?')

            
    logger.info('Phone Number -> {}'.format(phoneNumber))
    if phoneNumber is None:
        logger.debug('Phone Pumber is None')
        return build_validation_result(False,
                                       'phoneNumber',
                                       'Could you provide me with your phone number?')
    elif len(phoneNumber) != 10:
        logger.debug('Invalid Phone Pumber-> {}'.format(phoneNumber))
        return build_validation_result(False,
                                       'phoneNumber',
                                       'Please enter a valid 10-digit phone number.')
    if emailAddress is None:
        logger.debug('Email Address is None')
        return build_validation_result(False,
                                       'emailAddress',
                                       'Awesome!. Lastly, could you give me your email address so that I can send you my suggestions?')
    elif (not re.fullmatch(regex, emailAddress)):
        logger.debug('Invalid Email Address-> {}'.format(emailAddress))
        return build_validation_result(False,
                                       'emailAddress',
                                       'Please enter a valid email address.')

    logger.info('Successfully validated all the slots\n')                                   
    
    return build_validation_result(True, None, None)
    
    
    

def welcome(intent_request):
    intent_name = intent_request['sessionState']['intent']['name']
    return close(intent_request['sessionState']['sessionAttributes'],
                 intent_name,
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Hey there, How may I serve you today?'})

def thankYou(intent_request):
    intent_name = intent_request['sessionState']['intent']['name']
    return close(intent_request['sessionState']['sessionAttributes'],
                 intent_name,
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'My pleasure, Have a great day!!'})


def dispatch(intent_request):
    """
    Called when the user invokes an intent which has code hook as this Lambda function.
    """

    intent_name = intent_request['sessionState']['intent']['name']
    
    logger.info('dispatch sessionId={}, intentName={}'.format(intent_request['sessionId'], intent_name))
    logger.debug('Intent Request-> {}'.format(intent_request))
    
    # Check and perform validation depending on Intent name
    
    if intent_name == 'DiningSuggestionsIntent':
        return dining_suggestions(intent_request)
    elif intent_name == "Greeting":
        return welcome(intent_request)
    elif intent_name == 'ThankYouIntent':
        return thankYou(intent_request)
        
   
        

    raise Exception('Intent with this name ' + intent_name + ' is not supported')

                  
def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default set the user request to the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    #logger.info('event.bot.name={}'.format(event['bot']['name']))
    logger.info(event)

    res = dispatch(event)
    logger.info('Result->\n\n')
    logger.info(res)
    return res
