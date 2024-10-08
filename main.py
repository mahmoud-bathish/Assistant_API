import json
import os
from time import sleep
from packaging import version
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
from openai import OpenAI
from dotenv import load_dotenv

from Functions.GermanKitchenWarFunctions import get_news

# Load environment variables from .env file
load_dotenv()

# Check OpenAI version is correct

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not OPENAI_API_KEY:
    raise ValueError("Error: OPENAI_API_KEY is not set in the environment variables")

required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)
if current_version < required_version:
    raise ValueError(f"Error: OpenAI version {openai.__version__} is less than the required version 1.1.1")
else:
    print("OpenAI version is compatible.")

# Start FastAPI app
app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Init client
client = OpenAI(api_key=OPENAI_API_KEY)

class ChatRequest(BaseModel):
    assistant_id: str
    thread_id: str
    message: str

@app.get("/start")
async def start_conversation():
    print("Starting a new conversation...")  # Debugging line
    thread = client.beta.threads.create()
    print(f"New thread created with ID: {thread.id}")  # Debugging line
    return {"thread_id": thread.id}

@app.post("/chat")
async def chat(request: ChatRequest):
    assistant_id = request.assistant_id
    thread_id = request.thread_id
    user_input = request.message

    if not thread_id:
        print("Error: Missing thread_id")  # Debugging line
        raise HTTPException(status_code=400, detail="Missing thread_id")

    print(f"Received message: {user_input} for thread ID: {thread_id}")  # Debugging line

    # Add the user's message to the thread
    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=user_input)

    # Run the Assistant
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)


    # Check if the Run requires action (function call)
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id= thread_id,
            run_id= run.id
        )
        print(f"Run Status: {run_status.model_dump_json(indent=4)}")
        if run_status.status == "completed":
            break
        elif run_status.status == "requires_action":
            print("FUNCTION CALLING NOW...")
            call_required_functions(
                required_actions=run_status.required_actions.submit_tool_outputs.model_dump(),
                run_id= run.id,
                thread_id= thread_id
            )
            break
        sleep(0.5)  # Wait for a second before checking again

    # Retrieve and return the latest message from the assistant
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    response = messages.data[0].content[0].text.value

    print(f"Assistant response: {response}")  # Debugging line
    return {"response": response}

def call_required_functions(required_actions, run_id, thread_id):
    tools_outputs = []
    for action in required_actions["tool_calls"]:
        func_name = action["function"]["name"]
        arguments = json.loads(action["function"]["arguments"])
        if func_name == "get_news":
            output = get_news(topic=arguments["topic"])
            print(f"Output: {output}")
            tools_outputs.append({"tool_call_id": action["id"], "output": output})
        else:
            raise ValueError(f"Unknown function: {func_name}")
    print(f"Submitting outputs back to the Assistant...")
    client.beta.threads.runs.submit_tool_outputs(
        thread_id= thread_id,
        run_id= run_id,
        tool_outputs= tools_outputs
    )    

# Run server
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8080)
