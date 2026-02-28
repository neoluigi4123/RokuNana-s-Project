"""
Core module where the llm agent is implemented.
"""
import config
from mistralai import Mistral
from typing import Any
import os
import json

class LLM:
    def __init__(self, model: str, api_key: str = str(config.MISTRAL_API_KEY)):
        self.model = model
        self.client = Mistral(api_key=api_key)
        self.context: list[Any] = [
            {
                "role": "system",
                "content": config.SYSTEM_PROMPT,
            }
        ]
    def generate(self, prompt: str):
        """Generates a response from the LLM based on the given prompt.
        Args:
            prompt (str): The input prompt to generate a response for.
        Returns:
            str: The generated response from the LLM.
        """
        self.add_to_context(prompt)
        
        result = None
        
        # Loop until we get a result that has text content
        while not result or not result.content:
            chat_response = self.client.chat.complete(
                model = self.model,
                messages = self.context,
            )
            result = chat_response.choices[0].message

    def add_to_context(self, content: str, role: str = 'user') -> None:
        """Adds contents to the context.
        Args:
            role (str): the role of the message(can be: "user","system","assistant").
            content (str): the content of the message.
        Returns:
            None.
        """
        self.context.append({
            "role": role,
            "content": content
        })
        try:
            directory = os.path.dirname("local_data/context.json")
            os.makedirs(directory, exist_ok=True)
            with open("local_data/context.json", "w", encoding="utf-8") as f:
                json.dump(self.context, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving context: {e}")

        

if __name__ == "__main__":
    assistant = LLM(model=config.DEFAULT_MODEL)
    response = assistant.generate("What is the capital of France?")
    print(response)
    print(f"context:\n{assistant.context}")