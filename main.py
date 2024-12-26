import os
import json
import base64
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect, Say, Stream
from twilio.rest import Client

from database import get_product_info_from_pinecone

from dotenv import load_dotenv
import logging
import sqlite3
import time

load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PORT = int(os.getenv('PORT', 5050))
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")


SYSTEM_MESSAGE = (
    "You are an AI assistant specialized in home loan products. "
    "You will provide accurate and concise answers based on the data stored in Pinecone. "
    "You will ask the caller a few questions to assist the loan officer. "
    "Always stay positive and do not go outside loan assistance while talking with the customer."
)
VOICE = 'alloy'
LOG_EVENT_TYPES = [
    'response.content.done',
    'rate_limits.updated',
    'response.done',
    'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started',
    'session.created',
    'response.text.done',
    'conversation.item.input_audio_transcription.completed'
]
SHOW_TIMING_MATH = False
MAKE_WEBHOOK_URL = os.getenv('MAKE_WEBHOOK_URL')
sessions = {}

app = FastAPI()

if not all([OPENAI_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
    raise ValueError("Missing Twilio or OpenAI configuration in the .env file.")


client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
@app.get("/", response_class=JSONResponse)
async def index_page():
    return {"message": "Twilio Outgoing Call Server is running!"}

# @app.api_route("/incoming-call", methods=["GET", "POST"])
# async def handle_incoming_call(request: Request):
#     """Handle incoming call and return TwiML response to connect to Media Stream."""
#     response = VoiceResponse()
#     # <Say> punctuation to improve text-to-speech flow
#     response.say("Please wait while we connect your call to the A. I. voice assistant, powered by Twilio and the Open-A.I. Realtime API")
#     response.pause(length=1)
#     response.say("O.K. you can start talking!")
#     host = request.url.hostname
#     connect = Connect()
#     connect.stream(url=f'wss://{host}/media-stream')
#     response.append(connect)
#     return HTMLResponse(content=str(response), media_type="application/xml")

# @app.get("/query-pinecone", response_class=JSONResponse)
@app.api_route("/query-pinecone", methods=["GET", "POST"], response_class=JSONResponse)
async def query_pinecone(query: str):
    """Endpoint to query Pinecone and return results."""
    results = get_product_info_from_pinecone(query)
    return {"results": results}

# @app.post("/make-call")
@app.api_route("/make-call", methods=["GET", "POST"])
async def make_outgoing_call(to: str, name: str):
    """Initiate an outgoing call and connect it to the AI assistant."""
    if not to or not name:
        raise HTTPException(status_code=400, detail="The 'to' phone number and 'name' are required.")

    # Generate TwiML for the call
    twiml_url = f"{os.getenv('HOSTNAME')}/twiml"

    try:
        call = client.calls.create(
            to=to,
            from_=TWILIO_PHONE_NUMBER,
            url=twiml_url
        )
        sessions[call.sid] = {"name": name, "contact_number": to, "transcript": '', "streamSid": None}
        return {"message": "Call initiated successfully", "call_sid": call.sid}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initiating call: {e}")


# @app.get("/twiml", response_class=HTMLResponse)
@app.api_route("/twiml", methods=["GET", "POST"], response_class=HTMLResponse)
async def twiml_response():
    """Generate TwiML response for the outgoing call."""
    response = VoiceResponse()
    response.say(
        "Hello! You are now connected to an AI voice assistant for Home Loan queries.",
        voice="alice"
    )
    response.pause(length=1)
    response.say("Please wait while we connect you to the assistant.", voice="alice")

    # Connect the call to the WebSocket for media streaming
    connect = Connect()
    # connect.stream(url=f"wss://{os.getenv('HOSTNAME')}/media-stream")
    connect.stream(url="wss://daaf-2409-40c4-1176-7686-1d75-947e-41f6-a5f3.ngrok-free.app/media-stream")
    response.append(connect)
    
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between Twilio and OpenAI."""
    print("Client connected")
    await websocket.accept()

    session_id = websocket.headers.get('x-twilio-call-sid', f'session_{int(time.time())}')
    session = sessions.get(session_id, {"transcript": '', "streamSid": None})
    sessions[session_id] = session

    async with websockets.connect(
        'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01',
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    ) as openai_ws:
        await initialize_session(openai_ws)

        # Connection specific state
        stream_sid = None
        latest_media_timestamp = 0
        last_assistant_item = None
        mark_queue = []
        response_start_timestamp_twilio = None
        
        # # @openai_ws.on('message')
        # @websocket.on_event("message")
        # async def on_openai_message(data):
        #     try:
        #         response = json.loads(data)

        #         if response['type'] == 'response.audio.delta' and response.get('delta'):
        #             await websocket.send_json({
        #                 "event": "media",
        #                 "streamSid": stream_sid,
        #                 "media": {"payload": response['delta']}
        #             })

        #         if response['type'] == 'response.done':
        #             agent_message = response['response']['output'][0].get('content', [{}])[0].get('transcript', 'Agent message not found')
        #             session['transcript'] += f'Agent: {agent_message}\n'
        #             logging.info('Agent (%s): %s', session_id, agent_message)

        #         if response['type'] == 'conversation.item.input_audio_transcription.completed' and response.get('transcript'):
        #             user_message = response['transcript'].strip()
        #             session['transcript'] += f'User: {user_message}\n'
        #             logging.info('User (%s): %s', session_id, user_message)

        #         if response['type'] in LOG_EVENT_TYPES:
        #             logging.info('Received event: %s', response)

        #     except Exception as e:
        #         logging.error('Error processing OpenAI message: %s, Raw message: %s', str(e), data)


        async def receive_from_twilio():
            """Receive audio data from Twilio and send it to the OpenAI Realtime API."""
            nonlocal stream_sid, latest_media_timestamp
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    if data['event'] == 'media' and openai_ws.open:
                        latest_media_timestamp = int(data['media']['timestamp'])
                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": data['media']['payload']
                        }
                        await openai_ws.send(json.dumps(audio_append))
                    elif data['event'] == 'start':
                        stream_sid = data['start']['streamSid']
                        print(f"Incoming stream has started {stream_sid}")
                        response_start_timestamp_twilio = None
                        latest_media_timestamp = 0
                        last_assistant_item = None
                    elif data['event'] == 'mark':
                        if mark_queue:
                            mark_queue.pop(0)
            except WebSocketDisconnect:
                print("Client disconnected.")
                if openai_ws.open:
                    await openai_ws.close()
                await on_close(session_id, session, openai_ws)

        async def send_to_twilio():
            """Receive events from the OpenAI Realtime API, send audio back to Twilio."""
            nonlocal stream_sid, last_assistant_item, response_start_timestamp_twilio
            try:
                async for openai_message in openai_ws:
                    response = json.loads(openai_message)
                    if response['type'] in LOG_EVENT_TYPES:
                        print(f"Received event: {response['type']}", response)

                    if response.get('type') == 'response.audio.delta' and 'delta' in response:
                        audio_payload = base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')
                        audio_delta = {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": audio_payload
                            }
                        }
                        await websocket.send_json(audio_delta)

                        if response_start_timestamp_twilio is None:
                            response_start_timestamp_twilio = latest_media_timestamp
                            if SHOW_TIMING_MATH:
                                print(f"Setting start timestamp for new response: {response_start_timestamp_twilio}ms")

                        # Update last_assistant_item safely
                        if response.get('item_id'):
                            # last_assistant_item = response['item_id']
                            last_assistant_item = response.get('item_id')

                        await send_mark(websocket, stream_sid)

                    # # Handle customer query
                    # if response.get('type') == 'conversation.item.input_audio_transcription.completed' and response.get('transcript'):
                    #     user_message = response['transcript'].strip()
                    #     query = user_message.lower().replace("query", "").strip()
                    #     pinecone_results = get_product_info_from_pinecone(query)
                    #     response_text = "Here are the results from Pinecone: " + ", ".join([result['metadata']['product_info'] for result in pinecone_results])
                    #     print(f"User query: {user_message}, Pinecone results: {response_text}")
                    #     await send_response_to_twilio(response_text)


                    # Handle customer query
                    if response.get('type') == 'conversation.item.input_audio_transcription.completed' and response.get('transcript'):
                        user_message = response['transcript'].strip()
                        print(f"User Message: {user_message}")
                        logging.info(f"User Message: {user_message}")

                        # Add user message to the transcript
                        session['transcript'] += f"\nUser: {user_message}"
                        print(f"Updated Transcript: {session['transcript']}")
                        logging.info(f"Updated Transcript: {session['transcript']}")

                        query = user_message.lower().replace("query", "").strip()
                        logging.info(f"Query: {query}")

                        try:
                            pinecone_results = get_product_info_from_pinecone(query)
                            logging.info(f"Pinecone Results: {pinecone_results}")

                            if pinecone_results:
                                response_text = "Here are the results from Pinecone: " + ", ".join([result['metadata']['product_info'] for result in pinecone_results])
                            else:
                                response_text = "No results found in Pinecone for your query."

                            print(f"Pinecone Query Results for '{query}': {response_text}")
                            logging.info(f"Pinecone Query Results for '{query}': {response_text}")

                            await send_response_to_twilio(response_text)
                        except Exception as e:
                            logging.error(f"Error querying Pinecone: {e}")
                            await send_response_to_twilio("Sorry, there was an error processing your request.")

                    # Log user speech
                    if response.get('type') == 'input_audio_buffer.speech_stopped' and response.get('transcript'):
                        user_transcript = response['transcript'].strip()
                        print(f"User Transcript: {user_transcript}")
                        session['transcript'] += f"\nUser: {user_transcript}"
                        print(f"Updated Transcript: {session['transcript']}")
                        logging.info(f"Updated Transcript: {session['transcript']}")

                    # Trigger an interruption. Your use case might work better using `input_audio_buffer.speech_stopped`, or combining the two.
                    if response.get('type') == 'input_audio_buffer.speech_started':
                        print("Speech started detected.")
                        if last_assistant_item:
                            print(f"Interrupting response with id: {last_assistant_item}")
                            await handle_speech_started_event()
            except Exception as e:
                print(f"Error in send_to_twilio: {e}")
                await on_close(session_id, session, openai_ws)

        async def send_response_to_twilio(response_text):
            """Send a text response to Twilio."""
            response_item = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "input_text",
                            "text": response_text
                        }
                    ]
                }
            }
            await openai_ws.send(json.dumps(response_item))
            await openai_ws.send(json.dumps({"type": "response.create"}))        
        
        async def handle_speech_started_event():
            """Handle interruption when the caller's speech starts."""
            nonlocal response_start_timestamp_twilio, last_assistant_item
            print("Handling speech started event.")
            if mark_queue and response_start_timestamp_twilio is not None:
                elapsed_time = latest_media_timestamp - response_start_timestamp_twilio
                if SHOW_TIMING_MATH:
                    print(f"Calculating elapsed time for truncation: {latest_media_timestamp} - {response_start_timestamp_twilio} = {elapsed_time}ms")

                if last_assistant_item:
                    if SHOW_TIMING_MATH:
                        print(f"Truncating item with ID: {last_assistant_item}, Truncated at: {elapsed_time}ms")

                    truncate_event = {
                        "type": "conversation.item.truncate",
                        "item_id": last_assistant_item,
                        "content_index": 0,
                        "audio_end_ms": elapsed_time
                    }
                    await openai_ws.send(json.dumps(truncate_event))

                await websocket.send_json({
                    "event": "clear",
                    "streamSid": stream_sid
                })

                mark_queue.clear()
                last_assistant_item = None
                response_start_timestamp_twilio = None

        async def send_mark(connection, stream_sid):
            if stream_sid:
                mark_event = {
                    "event": "mark",
                    "streamSid": stream_sid,
                    "mark": {"name": "responsePart"}
                }
                await connection.send_json(mark_event)
                mark_queue.append('responsePart')

        await asyncio.gather(receive_from_twilio(), send_to_twilio())

        # @websocket.on('close')
        @websocket.on_event("close")
        async def on_close(session_id, session, openai_ws):
            logging.info('on_close called with session_id: %s', session_id)
            if openai_ws.ready_state == openai_ws.OPEN:
                await openai_ws.close()
            logging.info('Client disconnected (%s).', session_id)
            logging.info('Full Transcript:')
            logging.info(session['transcript'])

            logging.info('Final Caller Number: %s', session['contact_number'])

            # Extract required information from the transcript
            # This is a placeholder. You need to implement the actual extraction logic.
            interested_in_home_loan = "Yes"
            time_period_of_loan = "15 years"
            location_of_home = "New Delhi"
            any_other_home_loan = "No"

            logging.info("Storing data in database")
            await store_in_database({
                "name": session['name'],
                "contact_number": session['contact_number'],
                "interested_in_home_loan": interested_in_home_loan,
                "time_period_of_loan": time_period_of_loan,
                "location_of_home": location_of_home,
                "any_other_home_loan": any_other_home_loan,
                # "transcript": session['transcript']
            })

            del sessions[session_id]

        @openai_ws.on('error')
        # @websocket.on_event("error")
        async def on_error(error):
            logging.error('Error in the OpenAI WebSocket: %s', str(error))
            await on_close(session_id, session, openai_ws)

        async def send_error_response():
            await openai_ws.send_json({
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"],
                    "instructions": "I apologize, but I'm having trouble processing your request right now. Is there anything else I can help you with?",
                }
            })

logging.basicConfig(level=logging.INFO)
async def store_in_database(data):
    logging.info("Inserting data into database: %s", data)
    conn = sqlite3.connect('callbot.db', check_same_thread=False)
    try:
        c = conn.cursor()
        c.execute('''
            INSERT INTO call_details (name, contact_number, interested_in_home_loan, time_period_of_loan, location_of_home, any_other_home_loan, transcript)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['name'], data['contact_number'], data['interested_in_home_loan'], data['time_period_of_loan'], data['location_of_home'], data['any_other_home_loan'], data['transcript']))
        conn.commit()
        logging.info("Data inserted into call_details table: %s", data)
    except Exception as e:
        logging.error("Error inserting data into database: %s", str(e))
    finally:
        conn.close()

async def send_initial_conversation_item(openai_ws):
    """Send initial conversation item if AI talks first."""
    initial_conversation_item = {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "Hello there! I am an AI voice assistant powered by Twilio and the OpenAI Realtime API. I will ask you a few questions to assist our loan officer. Are you interested in a home loan?"
                }
            ]
        }
    }
    await openai_ws.send(json.dumps(initial_conversation_item))
    await openai_ws.send(json.dumps({"type": "response.create"}))


async def initialize_session(openai_ws):
    """Send initial session with OpenAI."""
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": VOICE,
            "instructions": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
        }
    }
    print('Sending session update:', json.dumps(session_update))
    await openai_ws.send(json.dumps(session_update))

    # Uncomment the next line to have the AI speak first
    await send_initial_conversation_item(openai_ws)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)