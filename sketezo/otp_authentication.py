# Let users type local numbers like 98765... (auto-parsed as India for example)
PHONENUMBER_DEFAULT_REGION = "IN"  # pick your main audience region. optional.  # noqa

# Use Twilio to deliver tokens
TWO_FACTOR_SMS_GATEWAY  = "two_factor.gateways.twilio.gateway.Twilio"
TWO_FACTOR_CALL_GATEWAY = "two_factor.gateways.twilio.gateway.Twilio"

# Twilio credentials (use env vars in production)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
# Either a Messaging Service SID for SMS OR a phone number as caller ID:
TWILIO_MESSAGING_SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID")  # preferred for SMS
TWILIO_CALLER_ID = os.getenv("TWILIO_CALLER_ID")  # verified Twilio number (used for calls; also fallback for SMS)
