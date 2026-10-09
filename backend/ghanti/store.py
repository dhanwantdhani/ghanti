"""DynamoDB access. Three tables, names from environment variables.

Schools  (PK school_id)
Calls    (PK school_id, SK sk)   sk is one of:
            call#<date>#<slot_id>      a decision for a slot
            forecast#<date>            the hourly forecast used that day
            ledger#<date>#<slot_id>    the after-the-fact score
            token#<token>              teacher link token -> date
         GSI TokenIndex (HASH token) for teacher links
Readings (PK station_id, SK ts_hour "YYYY-MM-DDTHH")
"""
import os
import json
import decimal
import boto3
from boto3.dynamodb.conditions import Key

_ddb = boto3.resource("dynamodb")


def _table(env_name):
    return _ddb.Table(os.environ[env_name])


def _clean(obj):
    """Convert floats to Decimal for DynamoDB and back for JSON."""
    return json.loads(json.dumps(obj), parse_float=decimal.Decimal)


def _plain(obj):
    if isinstance(obj, list):
        return [_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, decimal.Decimal):
        return float(obj) if obj % 1 else int(obj)
    return obj


# Schools --------------------------------------------------------------

def get_school(school_id):
    item = _table("SCHOOLS_TABLE").get_item(Key={"school_id": school_id}).get("Item")
    return _plain(item) if item else None


def put_school(school):
    _table("SCHOOLS_TABLE").put_item(Item=_clean(school))


# Calls, forecasts, tokens, ledger -------------------------------------

def put_forecast(school_id, date, hourly, issued):
    _table("CALLS_TABLE").put_item(Item=_clean({
        "school_id": school_id, "sk": f"forecast#{date}",
        "hourly": {str(h): v for h, v in hourly.items()}, "issued": issued,
    }))


def get_forecast(school_id, date):
    item = _table("CALLS_TABLE").get_item(Key={"school_id": school_id, "sk": f"forecast#{date}"}).get("Item")
    if not item:
        return None
    return {int(h): float(v) for h, v in item["hourly"].items()}


def put_call(school_id, date, call, token, status="SENT", message=""):
    item = dict(call)
    item.update({
        "school_id": school_id, "sk": f"call#{date}#{call['slot_id']}", "date": date,
        "token": token, "status": status, "message": message,
    })
    _table("CALLS_TABLE").put_item(Item=_clean(item))


def put_token(school_id, date, token):
    _table("CALLS_TABLE").put_item(Item={"school_id": school_id, "sk": f"token#{token}", "token": token, "date": date})


def get_calls(school_id, date):
    r = _table("CALLS_TABLE").query(
        KeyConditionExpression=Key("school_id").eq(school_id) & Key("sk").begins_with(f"call#{date}#"))
    return _plain(r.get("Items", []))


def update_call(school_id, date, slot_id, **fields):
    names = {f"#{k}": k for k in fields}
    values = {f":{k}": v for k, v in _clean(fields).items()}
    expr = "SET " + ", ".join(f"#{k} = :{k}" for k in fields)
    _table("CALLS_TABLE").update_item(
        Key={"school_id": school_id, "sk": f"call#{date}#{slot_id}"},
        UpdateExpression=expr, ExpressionAttributeNames=names, ExpressionAttributeValues=values)


def resolve_token(token):
    r = _table("CALLS_TABLE").query(IndexName="TokenIndex", KeyConditionExpression=Key("token").eq(token))
    for item in r.get("Items", []):
        if item["sk"].startswith("token#"):
            return item["school_id"], item["date"]
    return None, None


def put_ledger(school_id, date, slot_id, entry):
    item = dict(entry)
    item.update({"school_id": school_id, "sk": f"ledger#{date}#{slot_id}", "date": date, "slot_id": slot_id})
    _table("CALLS_TABLE").put_item(Item=_clean(item))


def get_ledger_for_date(school_id, date):
    r = _table("CALLS_TABLE").query(
        KeyConditionExpression=Key("school_id").eq(school_id) & Key("sk").begins_with(f"ledger#{date}#"))
    return {i["slot_id"]: _plain(i) for i in r.get("Items", [])}


def get_ledger(school_id, limit=60):
    r = _table("CALLS_TABLE").query(
        KeyConditionExpression=Key("school_id").eq(school_id) & Key("sk").begins_with("ledger#"),
        ScanIndexForward=False, Limit=limit)
    return _plain(r.get("Items", []))


# Readings ------------------------------------------------------------

def put_readings(station_id, rows, source="openaq"):
    """rows: list of (ts_hour, value)."""
    with _table("READINGS_TABLE").batch_writer(overwrite_by_pkeys=["station_id", "ts_hour"]) as b:
        for ts_hour, value in rows:
            b.put_item(Item=_clean({"station_id": str(station_id), "ts_hour": ts_hour, "pm25": value, "source": source}))


def get_readings(station_id, date):
    r = _table("READINGS_TABLE").query(
        KeyConditionExpression=Key("station_id").eq(str(station_id)) & Key("ts_hour").begins_with(date))
    return {int(i["ts_hour"][11:13]): float(i["pm25"]) for i in r.get("Items", [])}


def latest_reading(station_id):
    r = _table("READINGS_TABLE").query(
        KeyConditionExpression=Key("station_id").eq(str(station_id)), ScanIndexForward=False, Limit=1)
    items = r.get("Items", [])
    return (items[0]["ts_hour"], float(items[0]["pm25"])) if items else (None, None)


if __name__ == "__main__":
    # Needs the three table env vars and AWS credentials.
    print(get_school(os.environ.get("LIVE_SCHOOL_ID", "demo-school")))
