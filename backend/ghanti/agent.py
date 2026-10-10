"""The Strands agent that plans a day.

Division of labour, stated once and enforced in code:
  the agent fetches the forecast and asks the rules for the calls through
  tools, then writes the message. It cannot change a call: the calls the
  rules return are what gets stored, and the agent's message is accepted
  only if it names every slot and every decision word exactly. If the agent
  fails, plan.py falls back to the deterministic path and a template.
"""
import os
import re
from strands import Agent, tool
from strands.models import BedrockModel
from ghanti import forecast, rules

SYSTEM = """You are Ghanti, which tells one school's PE teacher the call for each outdoor period tomorrow.
Procedure, always in this order:
1. Call get_forecast for the date.
2. Call decide_calls for the date. Its answer is final. Never change, add, remove or re-rank a decision.
3. Write the opening of the evening message to the teacher: at most two sentences, plain English,
   no emoji, no markdown. Sentence one: what the day's air looks like and when it is worst and best.
   Sentence two: what changes (which slots move or go indoors), or that nothing changes.
   Do not list every slot; the system appends the exact list after your text.
Your final reply must be those sentences only."""


def plan_with_agent(school, date, weekday, excluded_windows=None):
    """Run the agent for one school and date.

    Algorithm: build two tools closed over the school. get_forecast fetches
    Open-Meteo hourly PM2.5 for the date (archive if the date is past).
    decide_calls runs rules.decide with the school's slots and windows and
    records the result. Run the agent with a one-line task; take its final
    text as the message; accept the message only if every slot label and
    decision word appears in it. Return (calls, hourly, message_or_None, trace).

    Args:
        school: dict as stored in the Schools table (name, lat, lon, slots, move_windows).
        date: "YYYY-MM-DD". weekday: "mon".."sun".
        excluded_windows: set of "HH:MM" a teacher has ruled out.
    Returns:
        tuple(calls: list of dict, hourly: dict, message: str or None, trace: list of str)
    """
    from handlers.common import slots_from_school, today
    trace = []
    box = {}

    @tool
    def get_forecast(date: str) -> dict:
        """Hourly PM2.5 forecast in ug/m3 for the school on a date, keyed by hour of day (0-23). CAMS model via Open-Meteo."""
        hourly = forecast.fetch_for_date(school["lat"], school["lon"], date)
        box["hourly"] = hourly
        trace.append(f"get_forecast({date}): {len(hourly)} hours, 08:00={round(hourly.get(8, 0))} 13:00={round(hourly.get(13, 0))}")
        return {str(h): round(v, 1) for h, v in hourly.items()}

    @tool
    def decide_calls(date: str) -> list:
        """Ghanti's fixed rules decide each outdoor slot for the date: OUTDOORS, CAUTION, MOVE (with move_to), INDOORS or NO_CHANGE. This result is final."""
        hourly = box.get("hourly") or {}
        calls = [c.to_dict() for c in rules.decide(slots_from_school(school), hourly, school.get("move_windows", []), weekday, excluded_windows)]
        box["calls"] = calls
        trace.append("decide_calls: " + ", ".join(f"{c['label']}={c['call']}" + (f"->{c['move_to']}" if c.get("move_to") else "") for c in calls))
        return calls

    model = BedrockModel(model_id=os.environ.get("BEDROCK_MODEL_ID", "apac.amazon.nova-lite-v1:0"),
                         region_name=os.environ.get("AWS_REGION", "ap-south-1"), temperature=0.2, max_tokens=400)
    agent = Agent(model=model, tools=[get_forecast, decide_calls], system_prompt=SYSTEM, callback_handler=None)
    try:
        result = agent(f"Plan {date} ({weekday}) for {school['name']}, {school.get('city', '')}.")
        text = str(result).strip()
    except Exception as e:
        trace.append(f"agent error: {type(e).__name__}")
        return box.get("calls"), box.get("hourly"), None, trace
    calls = box.get("calls")
    if not calls:
        trace.append("agent never called decide_calls")
        return None, box.get("hourly"), None, trace
    prose = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.S).strip()
    prose = " ".join(prose.split())
    if not prose or len(prose) > 600:
        trace.append("agent prose rejected: empty or too long")
        return calls, box.get("hourly"), None, trace
    trace.append("agent prose accepted; exact slot lines appended by the rules")
    return calls, box.get("hourly"), prose, trace


def compose(school_name, date, prose, calls, teacher_url=None):
    """Final message: the agent's two sentences, then one exact line per call from the rules."""
    from ghanti.messaging import template_text
    body = template_text(school_name, date, calls, teacher_url)
    lines = body.split("\n")
    return "\n".join([lines[0], prose] + lines[1:])


if __name__ == "__main__":
    # Needs AWS credentials with Bedrock access. Uses the seed school.
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from scripts.seed_school import SCHOOL
    calls, hourly, prose, trace = plan_with_agent(SCHOOL, "2025-11-12", "wed")
    print("\n".join(trace)); print("---"); print(compose(SCHOOL["name"], "2025-11-12", prose or "(fallback: no prose)", calls))
