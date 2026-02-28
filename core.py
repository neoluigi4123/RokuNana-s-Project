"""
kawaiibaka.py
KawaiiBaka's brain and main module
"""

import copy
import re
import json
import requests
import base64
from typing import List, Literal, Optional, Union, Type, Annotated
from pydantic import BaseModel, Field, model_validator, create_model

import tools
import config
import google_calendar_tools

# - - - Tools - - -

class Web(BaseModel):
    """Web search tool | requires 'feedback' sometimes"""
    type: Literal["browsing"] = "browsing"
    query: str = Field(..., description="Search query or URL")
    mode: Literal["web", "gif", "youtube"] = Field(..., description="Mode of the search")

class PythonExecution(BaseModel):
    """Python code execution tool | requires 'feedback'"""
    type: Literal["pythonExecution"] = "pythonExecution"
    script: str = Field(..., description="Python script to execute")

class VoiceMessageGeneration(BaseModel):
    """Voice message generation tool | does NOT require 'feedback'"""
    type: Literal["voiceMessageGeneration"] = "voiceMessageGeneration"
    text: str = Field(..., description="Text to convert to voice message")

class Attachments(BaseModel):
    """Attachment tool | does NOT require 'feedback'"""
    type: Literal["attachments"] = "attachments"
    path: str = Field(..., description="Path to the attachment file")

class GetEvent(BaseModel):
    """Get an event from the calendar | requires 'feedback'"""
    type: Literal["getEvent"] = "getEvent"
    date: Optional[str] = Field(None, description="Date for which to get events (YYYY-MM-DD). Leave empty to use today's date.")

class SearchEvent(BaseModel):
    """Search events in the calendar | requires 'feedback'"""
    type: Literal["searchEvent"] = "searchEvent"
    query: str = Field(..., description="Query to search events")

class CreateEvent(BaseModel):
    """Create a calendar event | requires 'feedback'"""
    type: Literal["createEvent"] = "createEvent"
    title: str = Field(..., description="Title of the event")
    date: str = Field(..., description="Date of the event (YYYY-MM-DD). You can use natural language like 'today' or 'tomorrow'.")
    time: Optional[str] = Field(None, description="Time of the event (HH:MM)")

class UpdateEvent(BaseModel):
    """Update a calendar event | requires 'feedback'"""
    type: Literal["updateEvent"] = "updateEvent"
    event_id: str = Field(..., description="ID of the event to update")
    title: Optional[str] = Field(None, description="New title of the event")
    date: Optional[str] = Field(None, description="New date of the event (YYYY-MM-DD)")
    time: Optional[str] = Field(None, description="New time of the event (HH:MM)")

class DeleteEvent(BaseModel):
    """Delete a calendar event | requires 'feedback'"""
    type: Literal["deleteEvent"] = "deleteEvent"
    event_id: str = Field(..., description="ID of the event to delete")

class FindFreeSlot(BaseModel):
    """Find a free time slot in the calendar | requires 'feedback'"""
    type: Literal["findFreeSlot"] = "findFreeSlot"
    date: str = Field(..., description="Date to find free slots (YYYY-MM-DD)")
    duration: int = Field(..., description="Duration of the free slot in minutes")

class DailySummary(BaseModel):
    """Get a daily summary of events | requires 'feedback'"""
    type: Literal["dailySummary"] = "dailySummary"
    date: str = Field(..., description="Date for the summary (YYYY-MM-DD)")

# - - - MPC - - -

ToolUnion = Annotated[
    Union[Web, PythonExecution, VoiceMessageGeneration, Attachments, GetEvent, SearchEvent, UpdateEvent, DeleteEvent, FindFreeSlot, DailySummary],
    Field(discriminator='type')
]

class User(BaseModel):
    name: str = Field(..., description="Name of the user")
    current_emotion: str = Field(..., description="Current emotion of the user")
    engagement_level: int = Field(..., ge=0, le=100, description="Engagement level (0-100)")
    act_recognition: str = Field(..., description="Action recognition of the user")


class MessageSchema(BaseModel):
    users: List[User] = Field(..., description="State of users in the conversation (Excluding yourself)")

    summary: str = Field(..., description="Summary of the conversation so far")
    conversation_disentanglement: int = Field(..., ge=0, le=100, description="How distant the conversation is (0-100)")
    discourse_structure: str = Field(..., description="Structure of the discourse (narrative, descriptive, Q&A, etc.)")

    # Persona Characteristics
    social_context: str = Field(..., description="Social context of the conversation")
    current_mood: str = Field(..., description="Your Current mood")
    compliance_willingness: int = Field(..., ge=0, le=100, description="Your willingness to comply with requests (0-100)")
    internal_monologue: str = Field(..., description="Your internal thoughts")
    proposed_tool: str = Field(..., description="Tools relevant to the current conversation that you propose to use (if any). Just name them, no need to explain how you would use them here.")
    
    tool: Optional[ToolUnion] = Field(None, description="Tool to use. Only one tool can be used at a time.")
    
    unknown_fact: Optional[str] = Field(None, description="A fact about user that you didn't know until now.")
    reply: Optional[str] = Field(None, description="Your reply (or ignorance). Leave empty if using a tool that don't require feedback.")
    target_user: Optional[str] = Field(None, description="The user you're replying to. Must be a single and valid nickname, not the name of the user.")

    @model_validator(mode='after')
    def validate_reply_logic(self):
        tool_used = self.tool
        if tool_used:
            requires_feedback = isinstance(tool_used, (Web, PythonExecution))
            if requires_feedback and self.reply is not None:
                self.reply = ""
        
        if self.reply:
            if not self.target_user:
                raise ValueError("A 'target_user' is required when a 'reply' is provided.")
        else:
            self.target_user = None

        return self

class LLM:
    def __init__(
        self,
        model_name: str,
        api_key: str = "",
        client: str = "https://api.mistral.ai",
        system_prompt: str = "You are a usefull assistant of the name RokuNana.",
    ):
        self.model_name = model_name
        self.client_url = client.rstrip('/')
        self.api_key = api_key
        
        # Generation state tracking
        self.state = {
            "tool_usage": {
                "selfieGeneration": 0,
                "voiceMessageGeneration": 0,
            },
            "thinking": 0,
            "Replying": 0,
            "done": 0,
        }

        self.context = []
        
        self.tool_mapping = {
            "web": Web,
            "pythonExecution": PythonExecution,
            "voiceMessageGeneration": VoiceMessageGeneration,
            "attachments": Attachments
        }

        self.system_prompt = system_prompt

    def _mistral_request(
        self,
        messages: list,
        stream: bool = False,
        **extra_payload,
    ) -> Union[requests.Response, dict]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": stream,
            **extra_payload,
        }

        resp = requests.post(
            f"{self.client_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=stream,
        )
        resp.raise_for_status()
        return resp if stream else resp.json()

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
    
    def _get_dynamic_schema(self) -> Type[BaseModel]:
        available_tools = []
        
        for tool_name, usage_count in self.state['tool_usage'].items():
            if usage_count == 0 and tool_name in self.tool_mapping:
                available_tools.append(self.tool_mapping[tool_name])

        if len(available_tools) > 1:
            DynamicToolUnion = Annotated[
                Union[tuple(available_tools)],
                Field(discriminator='type')
            ]
        elif len(available_tools) == 1:
            DynamicToolUnion = available_tools[0]
        else:
            DynamicToolUnion = type(None)

        DynamicSchema = create_model(
            'DynamicMessageSchema',
            __base__=MessageSchema,
            tool=(Optional[DynamicToolUnion], Field(None, description="Tool to use."))
        )
        
        return DynamicSchema

    def _get_object_field(self, key, text):
        pattern = rf'"{key}"\s*:\s*({{.*?}})'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        return None

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

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
            result = self._mistral_request(
                messages=[{"role": "user", "content": summarization_prompt}],
                stream=False,
                max_tokens=1024,
            )
            summary_text = (
                result["choices"][0]["message"]["content"].strip()
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

    def generate(
        self,
        rag: str | None = None,
        prompt: dict | None = None,
    ) -> str:
        """
        Generate a structured JSON response via the Mistral chat-completions
        endpoint (streaming SSE).

        *   ``rag`` is injected as an **assistant prefill** message
            (``"prefix": true``) so the model continues from that context.
        *   Tool calls are dispatched inline; tools that require feedback
            (``Web``, ``PythonExecution``) break out of the stream and
            expect a subsequent ``generate_response`` call.

        :param rag:    Retrieval-Augmented Generation context string.
        :param prompt: Optional new user/message dict to append before
                       generating.
        :returns:      The raw constructed response string (JSON).
        """

        # reset generation state
        self.state['thinking'] = 1
        self.state['Replying'] = 0
        self.state['done'] = 0

        self.prev_reply = {}
        self.reply = {
            'tool': None,
            'tar_usr': None,
            'message': None,
            'attachments': [],
            'unknown_fact': None,
        }

        if prompt:
            self.add_to_context(
                prompt['content'],
                prompt['role'],
                prompt.get('images'),
            )

        # build the schema-aware system prompt
        current_schema_class = self._get_dynamic_schema()
        schema_json = json.dumps(
            current_schema_class.model_json_schema(), indent=2
        )

        system_prompt = (
            f"{self.system_prompt} You must respond in JSON format "
            f"following this schema:\n{schema_json}\n"
            f"Do NOT wrap in markdown code blocks. Do NOT use triple backticks."
        )

        # assemble message list
        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
        ]

        for msg in self.context:
            role = msg["role"]
            # Mistral only accepts system / user / assistant / tool (for function-call results).  Map generic "tool" context note to "user" so the API always accepts them.
            if role == "tool":
                role = "user"

            if "images" in msg and msg["images"]:
                # Mistral vision format
                content = [
                    {"type": "text", "text": msg["content"]},
                    *[
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img}",
                            },
                        }
                        for img in msg["images"]
                    ],
                ]
                messages.append({"role": role, "content": content})
            else:
                messages.append({"role": role, "content": msg["content"]})

        # Schema reminder just before generation
        # messages.append({
        #     "role": "system",
        #     "content": (
        #         f"{schema_json}\n"
        #         "Follow this schema strictly. Do not repeat your last message."
        #     ),
        # })

        # RAG as assistant prefill
        if rag is not None:
            messages.append({
                "role": "assistant",
                "content": f"(Temporal memory: {rag})\n"+"""{
    "users": [""",
                "prefix": True,
            })

        response = self._mistral_request(
            messages=messages,
            stream=True,
            temperature=0.6,
            frequency_penalty=0.5,
            presence_penalty=0.6,            
        )

        constructed_response = ""
        tool_called = False

        CALENDAR_TOOL_TYPES = {
            "getEvent",
            "searchEvent",
            "createEvent",
            "updateEvent",
            "deleteEvent",
            "findFreeSlot",
            "dailySummary",
        }

        def _get_field(key: str, text: str) -> Optional[str]:
            """Extract a JSON string value by key."""
            pattern = rf'"{key}"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"'
            m = re.search(pattern, text)
            return m.group(1) if m else None

        def _get_array_field(key: str, text: str) -> Optional[list]:
            pattern = rf'"{key}"\s*:\s*(\[.*?\])'
            m = re.search(pattern, text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    return None
            return None

        for raw_line in response.iter_lines():
            if not raw_line:
                continue

            line_str = raw_line.decode("utf-8").strip()
            if not line_str.startswith("data: "):
                continue

            data_str = line_str[6:]
            if data_str == "[DONE]":
                break

            try:
                chunk_data = json.loads(data_str)
                choices = chunk_data.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                chunk_content = delta.get("content", "")
            except json.JSONDecodeError:
                continue

            if not chunk_content:
                continue

            constructed_response += chunk_content

            # live field extraction
            tool_json_str = self._get_object_field("tool", constructed_response)

            if tool_json_str:
                try:
                    tool_obj = json.loads(tool_json_str)

                    if not tool_called and "type" in tool_obj:
                        print(f"Tool found: {tool_obj['type']}")

                        # Basic tools
                        if tool_obj["type"] == "browsing":
                            query = tool_obj["query"]
                            mode = tool_obj["mode"]

                            if mode == "web":
                                web_result = tools.web(query)
                                self.add_to_context(
                                    f"query: {query}\n\n{web_result}",
                                    role="tool",
                                )
                                break

                            elif mode == "gif":
                                gif_link = tools.gif(query)
                                self.reply["message"] = gif_link
                                self.add_to_context(
                                    f"query: {query}\n\n{gif_link}",
                                    role="tool",
                                )

                            elif mode == "youtube":
                                youtube_link = tools.youtube(query)
                                self.add_to_context(
                                    f"query: {query}\n\n{youtube_link}",
                                    role="tool",
                                )
                                break

                        if tool_obj["type"].lower() == "pythonexecution":
                            script = tool_obj["script"]
                            python_result = tools.python_execution(script)
                            self.add_to_context(
                                f"script: {script}\n\nresult: {python_result}",
                                role="tool",
                            )
                            print(f"Script result: {python_result}")
                            break

                        if tool_obj["type"] == "voiceMessageGeneration":
                            text = tool_obj["text"]
                            voice_message = tools.voice_message_generation(text)
                            self.reply["attachments"].append(voice_message)
                            self.add_to_context(
                                f"Generated a voice message with text: {text}",
                                role="tool",
                            )

                        if tool_obj["type"] == "attachments":
                            file_path = tool_obj["path"]
                            self.reply["attachments"].append(file_path)
                            self.add_to_context(
                                f"Added attachment from path: {file_path}",
                                role="tool",
                            )
                        
                        # Calendar tools
                        if tool_obj["type"] in CALENDAR_TOOL_TYPES:
                            tool_type = tool_obj["type"]
                            # Build args dict from tool_obj, excluding 'type'
                            cal_args = {
                                k: v
                                for k, v in tool_obj.items()
                                if k != "type" and v is not None
                            }
                            print(f"Calendar tool: {tool_type} with args: {cal_args}")

                            try:
                                cal_result = google_calendar_tools.run_tool(
                                    tool_type, cal_args
                                )
                                result_str = json.dumps(cal_result, default=str)
                            except Exception as e:
                                result_str = json.dumps({"error": str(e)})
                                print(f"Calendar tool error: {e}")

                            self.add_to_context(
                                f"calendar tool: {tool_type}\n"
                                f"args: {json.dumps(cal_args)}\n\n"
                                f"result: {result_str}",
                                role="tool",
                            )
                            print(f"Calendar result: {result_str[:500]}")
                            break

                        tool_called = True
                        self.reply["tool"] = tool_obj

                except json.JSONDecodeError:
                    pass

            tar_usr = _get_field("target_user", constructed_response)
            if tar_usr is not None:
                self.reply["tar_usr"] = tar_usr
                self.state["Replying"] = 1
                self.state["thinking"] = 0

            message = _get_field("reply", constructed_response)
            if message is not None:
                self.reply["message"] = message
                self.state["done"] = 1

            attachments = _get_array_field("attachments", constructed_response)
            if attachments is not None:
                self.reply["attachments"] = attachments

            unknown_fact = _get_field("unknown_fact", constructed_response)
            if unknown_fact is not None or unknown_fact != "null":
                self.reply["unknown_fact"] = unknown_fact

            self.prev_reply = copy.deepcopy(self.reply)

            print(chunk_content, end="", flush=True)

        # post-processing
        if self.reply["unknown_fact"]:
            rag_embedding.write_memory(self.reply["unknown_fact"])

        if self.reply["message"]:
            self.add_to_context(self.reply["message"], role="assistant")
            chat_summary = _get_field("summary", constructed_response)
            if chat_summary is not None:
                try:
                    with open("chat_summary.txt", "w", encoding="utf-8") as f:
                        f.write(chat_summary)
                except Exception as e:
                    print(f"Error saving summary: {e}")

        return constructed_response


if __name__ == "__main__":
    import rag_embedding
    import config

    AI = LLM(
        model_name="mistral-large-latest",
        client="https://api.mistral.ai",
        system_prompt=config.SYSTEM_PROMPT,
    )

    r = AI.generate(
        prompt={
            "role": "user",
            "content": "Hello, can you add an event to my calendar for tomorrow at 3pm called 'Meeting with Bob' and then search the web for 'best pizza places near me' and give me a recommendation?",
        },
    )

    print(r)