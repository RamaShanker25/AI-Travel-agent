import os, json
from typing import List, Dict
from openai import AzureOpenAI
from .tools import tool_get_weather, tool_generate_itinerary, load_data_snapshot

# ✅ Azure OpenAI Client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
)

# ✅ This is your Azure DEPLOYMENT NAME, NOT model name
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT")

FUNCTIONS = [
    {
        "name": "get_destination_weather",
        "description": "Fetch weather for a destination id and date range.",
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
        "description": "Generate itinerary using CSV data.",
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
You are a production-grade AI Travel Planner.

================= CRITICAL GROUNDING RULES =================
1. You MUST use ONLY the following CSV-backed tools and data:
   - locations.csv → cities only
   - activities.csv → places & things to do
   - accommodations.csv → hotels only
   - transports.csv → transport only

2. You are STRICTLY FORBIDDEN from inventing:
   - Hotels
   - Tourist places
   - Activities
   - Prices
   - Durations
   - Transport routes

If a requested item is not present in the data, you MUST clearly say:
"This information is not available in the current database."

================= MANDATORY QUESTION FLOW =================
You MUST collect these three inputs before any itinerary generation:
✅ Destination (city)
✅ Date range
✅ Budget tier (Budget / Mid / Luxury)

If ANY of these is missing → you MUST ask for it and DO NOTHING ELSE.

================= TWO-STAGE PLANNING RULE =================

✅ STAGE 1 — TENTATIVE PLAN
Once Destination + Dates + Budget are available:
- You MUST immediately generate a:
  "TENTATIVE ITINERARY (BASED ON AVAILABLE DATA)"
- This MUST include:
  - Day-wise structure
  - Available places from activities.csv
  - Hotel options ONLY from accommodations.csv for the given budget
  - Weather summary (if available)
- You MUST clearly label this as *TENTATIVE*

✅ STAGE 2 — ACTIVITY REFINEMENT
After the tentative plan, you MUST ask:
"What type of activities do you prefer? (adventure, sightseeing, relaxation, kid-friendly)"

ONLY after this input:
- You may rearrange activities
- You may optimize timing
- You may rebalance days
- You MUST still use ONLY CSV data

================= TOOL USAGE RULE =================
You may call tools ONLY when:
- All required parameters are available
- The call matches the dataset exactly

================= STYLE & FORMAT =================
- Output should be structured
- Day-wise format
- Use bullet points
- Include approximate timing
- Include weather notes
- Include hotel names with price

  

================= DATA SNAPSHOT (GROUND TRUTH SAMPLE) =================
{data_snapshot}
"""


async def handle_chat_message(message: str, conversation: List[Dict]):
    system_prompt = build_system_prompt()

    messages = [{"role": "system", "content": system_prompt}]
    for m in conversation:
        messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})
    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model=AZURE_DEPLOYMENT_NAME,  # ✅ Azure requires DEPLOYMENT name here
        messages=messages,
        tools=[{"type": "function", "function": fn} for fn in FUNCTIONS],
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
            model=AZURE_DEPLOYMENT_NAME,
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

    return {"type": "reply", "reply": msg.content}
