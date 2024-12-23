import os
from dotenv import load_dotenv
load_dotenv()

print(os.getenv("TWILIO_PHONE_NUMBER"))
print(os.getenv("TWILIO_ACCOUNT_SID"))
print(os.getenv("TWILIO_AUTH_TOKEN"))

