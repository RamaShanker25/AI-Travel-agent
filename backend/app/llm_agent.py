import os, json
from typing import List, Dict
from openai import OpenAI
from .tools import tool_get_weather, tool_generate_itinerary, load_data_snapshot

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

FUNCTIONS = [
    {
        "name": "get_destination_weather",
        "description": "Fetch weather for a destination id and date range (returns summary+details).",
        "parameters": {
            "type": "object",
            "properties": {
                "location_id": {"type": "integer"},
                "start_date": {"type": "string"},
                "end_date": {"type": "string"}
            },
            "required": ["location_id", "start_date", "end_date"]
        }
    },
    {
        "name": "generate_itinerary",
        "description": "Generate a structured itinerary using CSV data. All factual details come from this tool.",
        "parameters": {
            "type": "object",
            "properties": {
                "destination_id": {"type": "integer"},
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
                "budget_tier": {"type": "string"},
                "interests": {"type": "string"}
            },
            "required": ["destination_id", "start_date", "end_date", "budget_tier"]
        }
    }
]

def build_system_prompt() -> str:
    data_snapshot = load_data_snapshot(max_locations=8)
    return f"""
You are a professional travel planner assistant.

RULES:
1. Never invent hotels, activities, transport, or costs.
2. Ask follow-up questions if destination, dates, or budget are missing.
3. Use tools when enough information is available.
4. You may add atmospheric tips (clothing, photography, etc).

Data snapshot (ground truth):
{data_snapshot}
"""

async def handle_chat_message(message: str, conversation: List[Dict]):
    system_prompt = build_system_prompt()

    messages = [{"role": "system", "content": system_prompt}]
    for m in conversation:
        messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})
    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=[
            {
                "type": "function",
                "function": fn
            } for fn in FUNCTIONS
        ],
        tool_choice="auto",
        temperature=0.2,
        max_tokens=1000
    )

    msg = response.choices[0].message

    # ✅ TOOL CALL HANDLING
    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        fn_name = tool_call.function.name
        fn_args = json.loads(tool_call.function.arguments)

        if fn_name == "get_destination_weather":
            tool_result = await tool_get_weather(
                fn_args["location_id"],
                fn_args["start_date"],
                fn_args["end_date"]
            )
        elif fn_name == "generate_itinerary":
            tool_result = await tool_generate_itinerary(fn_args)
        else:
            tool_result = {"error": "Unknown tool"}

        followup = client.chat.completions.create(
            model=MODEL,
            messages=[
                *messages,
                msg,
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result)
                }
            ],
            temperature=0.2,
            max_tokens=1500
        )

        final_text = followup.choices[0].message.content
        return {"type": "final", "reply": final_text}

    # ✅ NORMAL TEXT RESPONSE
    return {"type": "reply", "reply": msg.content}
