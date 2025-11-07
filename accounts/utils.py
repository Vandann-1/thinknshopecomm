# accounts/utils.py
from twilio.rest import Client
from django.conf import settings
from .twilio_credentials import TWILIO_AUTH_TOKEN,TWILIO_PHONE_NUMBER,TWILIO_SID



def send_otp(phone, otp):
    account_sid = TWILIO_SID
    auth_token = TWILIO_AUTH_TOKEN
    client = Client(account_sid, auth_token)
    
    message = client.messages.create(
        body=f"Your OTP is {otp}",
        from_=TWILIO_PHONE_NUMBER,
        to=phone
    )
    return message.sid
