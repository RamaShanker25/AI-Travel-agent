\
    import os, json
    import openai
    from typing import List, Dict
    from .tools import tool_get_weather, tool_generate_itinerary, load_data_snapshot

    openai.api_key = os.getenv("OPENAI_API_KEY", "")

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
            "description": "Generate a structured itinerary using CSV data. All factual details should come from this tool's output.",
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
        data_snapshot = load_data_snapshot(max_locations=12)
        system = f\"\"\"You are a professional travel planner assistant. Use the provided tools to fetch factual information from the application's CSV dataset.
    RULES:
    1) Do NOT invent factual items such as hotel names, activity durations, distances, transport modes, or costs. Any factual detail must come from the tools.
    2) You may ask follow-up questions when required (destination, dates, budget_tier).
    3) You may produce atmospheric/advisory language (packing tips, clothing, photography suggestions).
    4) When enough information is gathered, call the appropriate tool(s) - typically get_destination_weather and generate_itinerary - using function calling.
    Data snapshot (sample of CSV rows to help grounding):
    {data_snapshot}
    \"\"\"
        return system

    async def handle_chat_message(message: str, conversation: List[Dict]):
        system = build_system_prompt()
        messages = [{"role": "system", "content": system}]
        for m in conversation:
            messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})
        messages.append({"role": "user", "content": message})

        resp = openai.ChatCompletion.create(
            model=MODEL,
            messages=messages,
            functions=FUNCTIONS,
            function_call="auto",
            temperature=0.2,
            max_tokens=1000,
        )

        choice = resp["choices"][0]
        msg = choice["message"]

        if msg.get("function_call"):
            fname = msg["function_call"]["name"]
            fargs = json.loads(msg["function_call"].get("arguments", "{}"))

            if fname == "get_destination_weather":
                tool_result = await tool_get_weather(fargs["location_id"], fargs["start_date"], fargs["end_date"])
            elif fname == "generate_itinerary":
                tool_result = await tool_generate_itinerary(fargs)
            else:
                tool_result = {"error": f"Unknown tool {fname}"}

            messages.append({"role": "assistant", "content": None, "function_call": msg["function_call"]})
            messages.append({"role": "function", "name": fname, "content": json.dumps(tool_result)})
            followup = openai.ChatCompletion.create(
                model=MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=1500
            )
            final = followup["choices"][0]["message"]["content"]
            return {"type": "final", "reply": final, "tool": fname, "tool_output": tool_result}

        return {"type": "reply", "reply": msg.get("content", "")}
