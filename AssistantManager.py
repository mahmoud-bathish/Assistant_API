import json
from dotenv import load_dotenv
import openai
import os

import time
import logging
from datetime import datetime
import requests
import streamlit as st
from Functions.GermanKitchenWarFunctions import get_news
load_dotenv()

news_api_key = os.environ.get("NEWS_API_KEY")
client = openai.OpenAI()

model = "gpt-3.5-turbo-16k"  # "gpt-4-1106-preview"



class AssistantManager:
    thread_id = None
    assistant_id = None

    def __init__(self, model:str = model):
        self.client = client
        self.model = model
        self.assistant = None,
        self.thread = None
        self.run = None
        self.summary = None

        if AssistantManager.assistant_id:
            self.assistant = self.client.beta.assistants.retrieve(
                assistant_id = AssistantManager.assistant_id
            )
        if AssistantManager.thread_id:
            self.thread = self.client.beta.threads.retrieve(
                thread_id = AssistantManager.thread_id
            )
    
    def create_assistant(self, name, instructions,tools):
        if not self.assistant:
            assistant_obj = self.client.beta.assistants.create(
            name = name,
            instructions = instructions,
            tools = tools,
            model= self.model
        )
        AssistantManager.assistant_id = assistant_obj.id
        self.assistant = assistant_obj
        print(f"Assistant created with ID: {self.assistant_id}")

    def create_thread(self):
        if not self.thread:
            thread_obj = self.client.beta.threads.create()
            AssistantManager.thread_id = thread_obj.id
            self.thread = thread_obj
            print(f"Thread created with ID: {self.thread.id}")

    def add_message_to_thread(self, role, content):
        if self.thread:
            self.client.beta.threads.messages.create(
                role = role,
                thread_id = self.thread.id,
                content = content
            )
            print(f"Message added to thread: {self.thread.id}")
    
    def run_assistant(self, instructions):
        if self.thred and self.assistant:
            self.run = self.client.beta.threads.runs.create(
                thread_id= self.thread.id,
                assistant_id= self.assistant.id,
                instructions= instructions
            )
    
    def process_message(self):
        if self.thread:
            messages = self.client.beta.threads.messages.list(
                thread_id= self.thread.id
            )
            summary = []
            last_message = messages.data[0]
            role = last_message.content
            response = last_message.content[0].text.value
            summary.append(response)
            self.summary = "/n".join(summary)
            print(f"SUMMARY----> {role.capitalize()}: ===> {response}")
            
            # for msg in messages:
            #     role = msg.role
            #     content = msg.content[0].text.value
            #     print(f"SUMMARY----> {role.capitalize()}: ===> {content}")

    def call_required_functions(self, required_actions):
        if not self.run:
            return
        tools_outputs = []
        for action in required_actions["tool_calls"]:
            func_name = action["function"]["name"]
            arguments = json.loads(action["function"]["arguments"])
            if func_name == "get_news":
                output = get_news(topic=arguments["topic"])
                print(f"STAFFFF;;;;: {output}")
                final_str = ""
                for item in output:
                    final_str += "".join(item)
                tools_outputs.append({"tool_call_id": action["id"], "output": final_str})
            else:
                raise ValueError(f"Unknown function: {func_name}")
        print(f"Submitting outputs back to the Assistant...")
        self.client.beta.threads.runs.submit_tool_outputs(
            thread_id= self.thread.id,
            run_id= self.run.id,
            tool_outputs= tools_outputs
        )    
    # For Streamlit
    def get_summary(self):
        return self.summary

    def wait_for_completion(self):
        if self.thread and self.run:
            while True:
                time.sleep(5)
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id= self.thread.id,
                    run_id= self.run.id
                )
                print(f"Run Status: {run_status.model_dump_json(indent=4)}")
                if run_status.status == "completed":
                    self
                    break
                elif run_status.status == "requires_action":
                    print("FUNCTION CALLING NOW...")
                    self.call_required_functions(
                        required_actions=run_status.required_actions.submit_tool_outputs.model_dump()
                    )
                    break

    def run_steps(self):
        run_steps = self.client.beta.threads.runs.steps.list(
            thread_id= self.thread.id,
            run_id =  self.run.id
        )
        print(f"Run Steps::: {run_steps}")
        return run_steps.data




def main():
    # news = get_news("bitcoin")
    # print(news)
    manager = AssistantManager()
    st.title("News Summarizer")

    with st.form(key="user_input_form"):
        instructions = st.text_input("Enter topic:") 
        submit_button = st.form_submit_button(label="Run Assistant")
        if submit_button:
            manager.create_assistant(
                name = "News Summarizer",
                instructions="you are a presonal article summarizer Assistant who knows how to take a list of article's titles and descriptions and then write a short summary of all the news articles",
                tools=[
                    {
                        "type":"function",
                        "function": {
                            "name": "get_news",
                            "description": "Get the list of articles/news for the given topic",
                            "parameters":{
                                "type": "object",
                                "properties":{
                                    "topic": {
                                        "type": "string",
                                        "description": "The topic for the news, e.g. bitcoin"
                                    }
                                },
                                "required": ["topic"],
                            }
                        }
                    }
                ]
            )
            manager.create_thread()

            # Add message to thread
            manager.add_message_to_thread(
                role="user",
                content=f"summarize the news on this topic {instructions}?"
            )
            manager.run_assistant(instructions="Summarize the news")

            # wait for the assistant to complete
            manager.wait_for_completion()

            summary = manager.get_summary()
            st.write(summary)   
            st.text("Run Steps:")
            st.code(manager.run_steps(), line_numbers=True)
    pass

if __name__ == "__main__":
    main()