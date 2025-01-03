# Interactive Callbot

This is an interactive AI-powered callbot that integrates with Twilio for voice calls and uses OpenAI's Realtime API to handle real-time interactions. The callbot can:

- Greet users.
- Confirm details about the purpose of the call.
- Collect information about home loans and properties.
- Store transcriptions and call details for further processing.
- Provide dynamic and interactive conversations using speech recognition and text-to-speech capabilities.

---

## Features

1. **Interactive Calls:** Real-time speech recognition and synthesis for seamless conversations.
2. **Loan Inquiry Assistance:** Handles inquiries about home loans and collects lead details.
3. **Transcription Retrieval:** Fetches and processes call transcriptions from Twilio.
4. **OpenAI Integration:** Uses OpenAI's Realtime API for intelligent and dynamic responses.
5. **Error Handling:** Robust error handling to manage unexpected issues during calls or data processing.

---

## Prerequisites

1. **Python Environment:** Ensure Python 3.8 or above is installed.
2. **Twilio Account:** Active Twilio account with:
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - Transcription-enabled voice calls.
3. **OpenAI API Key:** Access to OpenAI's Realtime API.
4. **NGROK:** You need to setup ngrok url
5. **Dependencies:** Install the required Python libraries.

---

## Installation

### 1. Clone the Repository

```bash
$ git clone https://github.com/your-repository/interactive-callbot.git
$ cd interactive-callbot
```

### 2. Set Up Environment

Create a virtual environment and activate it:

```bash
$ python3 -m venv env
$ source env/bin/activate
```

### 3. Install Dependencies

```bash
$ pip install -r requirements.txt
```

### 4. Configure Environment Variables

Rename `.env.example` file to .env in the project directory and add all those APIs.

---

## Usage

### 1. Start the Callbot

Run the main script to initiate the callbot:

```bash
$ python main.py
```

### 2. Transcription Fetching

Use the `database.py` script for pinecone index database store of your product\_info.txt file:

```bash
$ python database.py
```

---

## Example Workflow

1. User receives a call from the bot.
2. The bot greets the user and asks about their home loan inquiry.
3. The bot collects relevant details and saves them.
4. Data is processed and stored for further use by loan officers.

---

## Future Improvements

- Add a database to store user interactions and call details.
- Improve NLP capabilities for more nuanced conversations.
- Support for multilingual interactions.
- Integrate with CRM systems for automatic lead management.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.
