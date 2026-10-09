# Ghanti: end-to-end execution

Follow this top to bottom. Every step says what to run, what you should see, and what to do if you do not see it. Time boxes assume one person coding and one person on data, people and video.

```
                 Oct 9 (today)              Oct 10 (Sat)                 Oct 11 (Sun)
Coder    | keys, deploy, seed, first call | teacher flow, Amplify, freeze | video support, submit
Partner  | teacher contact, timetable,    | chat ids, photos, README      | record, upload, submit
         | Telegram bot, phone numbers    | status table, replay check    |
```

## 0. What is already written (and tested here)

```
ghanti/
  template.yaml              SAM: 3 DynamoDB tables, 4 scheduled Lambdas (IST), 1 API Lambda with Function URL
  Makefile                   setup, test, local, seed, replay, record/plan/recheck/verify, deploy, outputs
  .env.example               every secret and setting; copy to .env
  README.md                  opening sentence, status table, data statement; fill the brackets
  backend/
    ghanti/rules.py          the deterministic call rules (tested, 13 tests pass)
    ghanti/dose.py           children-hours and micrograms avoided
    ghanti/forecast.py       Open-Meteo client (verified live today)
    ghanti/station.py        OpenAQ client, WAQI fallback
    ghanti/store.py          DynamoDB access
    ghanti/messaging.py      Nova text with template fallback, Telegram, SNS
    handlers/record.py       hourly station recorder
    handlers/plan.py         6 PM call
    handlers/recheck.py      6 AM station re-check
    handlers/verify.py       3 PM ledger
    handlers/api.py          /school /calls /ledger /replay /teacher /reply /sandbox
    scripts/seed_school.py   the live school record (EDIT THIS)
    scripts/dry_run_plan.py  make local (verified live today)
    scripts/make_replay.py   the labelled replay week (verified live today)
    tests/test_rules.py      unit tests
  frontend/index.html        one file, four views: Tomorrow, Teacher link, Try your school, Replay
```

Verified on Oct 9 from this machine: `make test` passes; `make local` fetched Lucknow's forecast and produced calls; `make replay` produced a five-day replay with two MOVE days; all five handlers import; the sandbox route returned a real call for Delhi.

Not yet verified (needs your AWS account and keys): deploy, DynamoDB writes, OpenAQ with a key, Bedrock access, Telegram delivery, Amplify.

## 1. Today, Oct 9

### 1.1 Accounts and keys (partner, 45 min, in parallel with 1.2)

- [ ] OpenAQ key: register at https://explore.openaq.org/register, copy the key from https://explore.openaq.org/account.
- [ ] Telegram bot: open @BotFather in Telegram, `/newbot`, name it Ghanti, copy the token. Both of you send `/start` to the bot. Then open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and copy each `chat.id`. One is the coordinator, one is the teacher for now.
- [ ] WAQI token (required, not optional): https://aqicn.org/data-platform/token/. Measured on Oct 9: OpenAQ's Indian station data runs about 43 hours behind, so the 6 AM re-check and the 3 PM verify read WAQI (same CPCB stations, within the hour). OpenAQ still provides the archive and backfills the ledger a day or two later.
- [ ] AWS: one region for everything, us-east-1. In the Bedrock console, open the model catalog and confirm you can run Amazon Nova Lite in the playground. If it fails, request access or try `amazon.nova-micro-v1:0` for text; put the working id in `.env`.
- [ ] SNS: Text messaging, sandbox, add and verify both your phone numbers. Check the account spend limit (default is about 1 USD a month; at the international route's price that is roughly 24 messages, so send none until the video).
- [ ] Message a teacher at your old school: ask for a photo of the real timetable with assembly and PE times, and a 30-second voice note about when PE happens and whether the air has ever changed it. Ask permission to use their first name and the school's name.

What breaks if skipped: no OpenAQ key means no recorder, no re-check, no verification, and the ledger stays empty; no Telegram means no delivery; no teacher means an illustrative school.

### 1.2 Local setup and first run (coder, 20 min)

```
cd ghanti
cp .env.example .env            # fill OPENAQ_API_KEY, TELEGRAM_BOT_TOKEN, chat ids, BEDROCK_MODEL_ID
make setup
make test                       # expect: Ran 13 tests ... OK
make local                      # expect: tomorrow's hourly forecast and one call per slot
```

If `make local` fails with a network error, retry once; Open-Meteo has no key and no quota that you will hit.

### 1.3 Edit the live school (coder + partner, 20 min)

Edit `backend/scripts/seed_school.py`: real coordinates, real slot times from the timetable photo, honest headcounts, the ground's free windows, `weekdays` including `sat` if the school works Saturdays. Keep `school_id` as `demo-school` unless you change `LIVE_SCHOOL_ID` in `.env` too.

If the school has no Saturday classes, add its Saturday sports practice as a slot. If there is none, the first live call is for Monday and the ledger will be empty at submission; say so in the status table and lean on the replay.

### 1.4 Deploy (coder, 40 min)

Install the SAM CLI if needed (`brew install aws-sam-cli` or pip). Then:

```
make deploy                     # first run: answer the guided prompts; stack name ghanti; region us-east-1; allow IAM
make outputs                    # copy ApiUrl, SchoolsTableName, CallsTableName, ReadingsTableName
```

Put the three table names into `.env`. Paste `ApiUrl` into `frontend/index.html` as `API_BASE` (no trailing slash).

Expect: five Lambdas, three tables, four schedules in the console. If `sam deploy` fails on ScheduleV2, your SAM CLI is old; upgrade it. If it fails on Bedrock permissions, the policy is in the template; check the model id instead.

### 1.5 Seed, record, and the first real call (coder, 30 min)

```
make seed                       # expect: seeded demo-school into <table>
make record                     # expect: {'ok': True, 'station': '<name>', 'rows': N, 'latest': ...}
```

If `record` says "no PM2.5 station within 15 km", raise `radius_m` in `station.nearest_pm25_sensor` to 30000 and run again. If OpenAQ returns 401, the key is not in `.env`. If the station's `last_seen` is days old, pick another by changing the coordinates slightly or filtering; a dead station cannot verify anything.

At 6 PM IST (or now, if later):

```
make plan                       # expect: {'ok': True, 'date': '2026-10-10', 'calls': [...], 'used_model': True/False, 'sent': {...}}
```

Both Telegram chats receive the message with a button. If `used_model` is False, the template was used; check Bedrock access, but the product still works. If `sent.coordinator` is False, the chat id is wrong or the bot was never started.

Open `frontend/index.html` locally in a browser: the Tomorrow view shows the calls, the phone frame shows the message, the ledger is empty, the honesty panel names the station.

### 1.6 End of day checkpoint

- [ ] Readings table gaining a row every hour (check after 7 past the hour).
- [ ] Calls table has tomorrow's forecast, calls and a token.
- [ ] Teacher link opens from the Telegram button (local file for now; it will be the Amplify URL tomorrow).
- [ ] Teacher contact replied, or a second teacher has been asked.

## 2. Saturday, Oct 10

### 2.1 6:10 AM: re-check runs by itself

It is scheduled. Confirm in CloudWatch logs for RecheckFunction, or run `make recheck`. Expect `forecast holds` or a list of changed slots plus a Telegram update. Screenshot the Telegram message either way.

### 2.2 Morning: frontend live (coder, 60 min)

```
make frontend-zip
```

Amplify Hosting console, "Deploy without Git", upload `frontend.zip`. Copy the URL. Put it in `.env` as `PUBLIC_BASE_URL` and run `make deploy` again so teacher links point at it. Re-run `make plan` only if you want tonight's links regenerated now; otherwise they regenerate at 6 PM.

Walk the judge's path on a phone and a laptop from a fresh browser: `/#/` loads with calls; `/#/try` returns a call for any coordinates in under five seconds; `/#/replay` shows the November week after `make replay`; the teacher link from Telegram opens `/#/t/<token>` and OK / Can't work. Fix anything that fails before adding anything.

### 2.3 Teacher reply on camera (partner, 15 min)

On the teacher phone: open the link, tap Can't on one slot, pick "The ground or hall is taken then", add a note. The coordinator chat receives the change; the Tomorrow view shows the new plan. Record this screen; it is the 0:30 to 1:00 scene.

### 2.4 3:00 PM: verify runs by itself

Confirm in logs or `make verify`. Expect right/wrong counts and a Telegram summary. The Tomorrow view's ledger now has rows. Screenshot. If `unverified` is True, the station had no data for those hours; the row says "no station data", which is honest and still shows the loop.

### 2.5 Afternoon: finish (both, 3 hours)

- [ ] `make replay` so `/#/replay` is filled.
- [ ] README: fill every bracket; status table reflects reality (what ran, how many readings, how many ledger rows).
- [ ] Architecture diagram: a Mermaid block in the README listing the resources in `template.yaml`.
- [ ] Screenshots of the AWS console: the four schedules, the Lambdas, the tables, Bedrock model catalog, Amplify app. These go in the video.
- [ ] Optional, only if everything above is done: wrap `plan_for` in a Strands agent with four tools. Skip without regret.
- [ ] Freeze at 8 PM. No new features after this. 6 PM `plan` has run for Sunday; Telegram shows it.

## 3. Sunday, Oct 11

### 3.1 Record (both, 2 hours, morning light)

Three takes. Script, 3:00 total; product on screen by 0:30; AWS visible; data source stated.

| Time | Screen | Say |
|---|---|---|
| 0:00-0:12 | School ground or the real timetable photo | "Every morning, [400] children stand here for assembly. In a North Indian winter, that is the dirtiest hour of the school day." |
| 0:12-0:30 | Tomorrow view, replay toggled on, a November day | "Ghanti colours tomorrow's outdoor slots by the hourly forecast and makes one call per slot. Here: assembly moves to 1:20 PM, PE moves to 12:30." |
| 0:30-1:00 | Teacher phone: Telegram message, link, Can't, re-plan | "The teacher gets it on her phone. She cannot do 1:20. Ghanti re-plans only her slot." |
| 1:00-1:30 | Live ledger row from Saturday | "Every afternoon it checks the station. Saturday: forecast [n], measured [m], the call was [right/wrong]. It says so." |
| 1:30-1:50 | Try your school: judge's coordinates, instant call | "Any school, anywhere. Drop your coordinates, get tomorrow's call." |
| 1:50-2:25 | AWS console: schedules, Lambdas, tables, Bedrock, Amplify | "Four schedules on EventBridge in Indian time run four Lambdas. DynamoDB holds the calls and the station readings. Nova writes the message and never changes a call. Amplify serves the page." |
| 2:25-2:50 | Honesty panel | "Forecast from a 45-kilometre model, said on screen. Station name and age of its last reading, on screen. Replays labelled. The rules are a Python file you can read." |
| 2:50-3:00 | Live URL | "Ghanti. One school, one teacher, one call a day." |

Upload to YouTube (unlisted is fine if the form allows; public otherwise). Check the length is under 3:00.

### 3.2 Submit (partner, 30 min)

- [ ] Repo public; `.env` not committed (check `git log -p | grep -i token` returns nothing).
- [ ] Live URL opens from a phone on mobile data.
- [ ] Video link, live URL, repo link in the form.
- [ ] Blog post only if time remains; it is a separate prize.

## 4. If something breaks

| Symptom | Do this |
|---|---|
| Bedrock access denied | Set `BEDROCK_MODEL_ID` to a model that works in the playground; or leave it: the template text is used and the status table says "template" |
| OpenAQ station stale or missing | Change coordinates to the nearest live station's area; or set `WAQI_TOKEN` and use `waqi_now` in `recheck` only; ledger rows then say "no station data" |
| Telegram not delivering | Wrong chat id or bot not started; test with `curl "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<ID>&text=hi"` |
| Amplify URL fails | Serve `frontend/index.html` from an S3 bucket with static hosting; it is one file |
| Schedules did not fire | Run `make plan` / `make recheck` / `make verify` by hand and say "run by hand" in the status table |
| Live week is clean, every call OUTDOORS | Expected in October outside the north. The video leads with the labelled replay; the live ledger still proves the loop runs |

## 5. The questions a judge will ask, and the on-screen answers

- "Just make a rule." A rule is delivered to nobody at 6 PM, knows nothing about which window is free, and never checks itself. The ledger is the answer.
- "It is modelled data." Yes, said on screen; the morning re-check and the afternoon verification use the station.
- "Where is the AI?" Writing the message and reading the note. The call is rules, and we say so.
- "Only Delhi?" The sandbox works anywhere; the replay shows a northern winter; the rules are the same everywhere.
