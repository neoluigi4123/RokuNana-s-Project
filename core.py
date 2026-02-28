"""
Core module where the llm agent is implemented.
"""
import config
from mistralai import Mistral
from typing import Any
import os
import json
import copy
import base64

class LLM:
    def __init__(self, model: str):
        self.model = model
        self.client = Mistral()
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
        return result

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def add_to_context(
        self,
        content: str,
        role: str = 'user',
        images: list[str] | None = None,
    ) -> None:
        message: dict = {"role": role, "content": content}

        if images:
            encoded_images = []
            for img_path in images:
                try:
                    b64_img = self._encode_image(img_path)
                    encoded_images.append(b64_img)
                except Exception as e:
                    print(f"Error encoding image {img_path}: {e}")
            if encoded_images:
                message["images"] = encoded_images
            
        self.context.append(message)

        try:
            with open("context.json", "w", encoding="utf-8") as f:
                log_context = copy.deepcopy(self.context)
                for msg in log_context:
                    if "images" in msg:
                        msg["images"] = ["<base64_image_data>"]
                json.dump(log_context, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving context: {e}")

    def summarize_chat(self, num: int = 10):
        if len(self.context) <= num:
            return

        to_summarize = self.context[:num]
        keep_rest = self.context[num:]

        # Strip base64 image data before serializing
        sanitized = copy.deepcopy(to_summarize)
        for msg in sanitized:
            if "images" in msg:
                count = len(msg["images"])
                msg.pop("images")
                msg["content"] += f" [attached {count} image(s)]"

        summarization_prompt = (
            f"Summarize this conversation concisely:\n{json.dumps(sanitized, ensure_ascii=False)}"
        )

        try:
            result = self.client.chat.complete(
                model = self.model,
                messages = [{"role": "user", "content": summarization_prompt}],
                stream=False
            )
            summary_text = (
                result.choices[0].message.content
            )
        except Exception as e:
            print(f"Summarization failed: {e}")
            return

        new_context = [
            {"role": "user", "content": f"(Summary of past conversation: {summary_text})"}
        ] + keep_rest

        self.context.clear()
        self.context.extend(new_context)

        try:
            with open("context.json", "w", encoding="utf-8") as f:
                log_context = copy.deepcopy(self.context)
                for msg in log_context:
                    if "images" in msg:
                        msg["images"] = ["<base64_image_data>"]
                json.dump(log_context, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving context: {e}")

if __name__ == "__main__":
    assistant = LLM(model=config.DEFAULT_MODEL)
    response = assistant.generate("What is the capital of France?")
    print(response)
    print(f"context:\n{assistant.context}")