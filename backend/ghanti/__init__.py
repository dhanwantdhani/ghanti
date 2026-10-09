"""Ghanti: tomorrow's outdoor call for one school.

Package layout:
    rules.py      deterministic call rules (no AI)
    dose.py       children-hours and micrograms avoided
    forecast.py   Open-Meteo client (forecast and archive)
    station.py    OpenAQ client with WAQI fallback
    store.py      DynamoDB access
    messaging.py  Bedrock text, Telegram, SNS
"""
