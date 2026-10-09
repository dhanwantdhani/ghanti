# Ghanti: what you do by hand, step by step

Plain English. Do the steps in order. Each step says where to go, what to click, and what to copy. Keep a notes file open; you will paste about ten values into it.

If you are on Windows: install "WSL" first (open PowerShell as administrator, type `wsl --install`, restart). Then do everything below inside the Ubuntu window it gives you. On Mac, use the Terminal app.

---

## Part A: accounts and keys (about 1 hour, no coding)

### A1. OpenAQ key (air station data)
1. Go to https://explore.openaq.org/register and make an account with your email.
2. Confirm the email, log in, go to https://explore.openaq.org/account.
3. Copy the long "API key". Save it in your notes as OPENAQ_API_KEY.

### A1b. WAQI token (same stations, but within the hour; required)
OpenAQ's Indian data arrives one to two days late, so the morning re-check and the afternoon verification use WAQI instead.
1. Go to https://aqicn.org/data-platform/token/, enter your email, submit.
2. The token arrives by email within a minute. Save it as WAQI_TOKEN.

### A2. Telegram bot (how the teacher gets the message)
1. In Telegram, search for the user called BotFather and open it.
2. Send `/newbot`. It asks for a name: type `Ghanti`. It asks for a username: type something ending in bot, like `ghanti_school_bot`.
3. It replies with a long token like `123456:ABC-...`. Save it as TELEGRAM_BOT_TOKEN.
4. Search for your new bot by its username, open it, and press Start. Ask your teammate to do the same on their phone.
5. In a browser, open this address, replacing TOKEN with your token:
   `https://api.telegram.org/botTOKEN/getUpdates`
6. You will see text with `"chat":{"id":123456789`. There is one id for each person who pressed Start. Save yours as COORDINATOR_CHAT_ID and your teammate's as TEACHER_CHAT_ID. (When a real teacher joins later, they press Start too and you swap in their id.)

### A3. AWS account
1. Go to https://aws.amazon.com and create an account if you do not have one (needs a card; the hackathon credits cover the cost). Use the same email you registered for the hackathon with on AWS Builder Center.
2. Log in. In the top right, set the region to **US East (N. Virginia)**, which is called us-east-1. Use this region for everything.

### A4. AWS access keys (so the tools on your laptop can talk to AWS)
1. In the AWS search bar at the top, type IAM and open it.
2. Left menu: Users, then Create user. Name: `ghanti-dev`. Next.
3. Choose "Attach policies directly", tick **AdministratorAccess**. Next, Create user.
4. Open the user, go to the "Security credentials" tab, scroll to Access keys, Create access key. Choose "Command Line Interface (CLI)", tick the box, Next, Create.
5. Copy both values now (you cannot see the secret again later). Save as AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.

### A5. Bedrock (the model that writes the message)
1. In the AWS search bar type Bedrock, open Amazon Bedrock. Make sure the region is still N. Virginia.
2. Left menu: Playgrounds, then Chat/text. Click Select model, choose Amazon, then Nova Lite. Type "hello" and run it.
3. If it answers, you are done. Save `amazon.nova-lite-v1:0` as BEDROCK_MODEL_ID.
4. If it says you need access, left menu: Model access, Modify model access, tick the Nova models, submit. It is usually instant. If Nova Lite will not work, try Nova Micro and save `amazon.nova-micro-v1:0` instead.

### A6. SNS text messages (only for the video)
1. AWS search bar: SNS, open Amazon SNS. Left menu: Text messaging (SMS).
2. Under Sandbox destination phone numbers, Add phone number, enter yours with +91, you get a code by SMS, enter it. Do the same for your teammate's number.
3. Save both numbers as SMS_NUMBERS, like `+919812345678,+919876543210`.
4. Do not send test messages. The default monthly limit is about 1 US dollar, which is roughly 24 messages at India's international rate.

### A7. The teacher (the most important step, start it now)
Message a teacher at your old school. Ask for three things: a photo of the real timetable showing assembly and PE times, a 30-second voice note about when PE happens and whether the air has ever changed it, and permission to use their first name and the school's name. If they say no to the names, you will write "a PE teacher at a school in [city]" instead.

---

## Part B: install the tools (about 30 minutes)

Open Terminal (or your WSL Ubuntu window). Paste each line, press Enter, wait for it to finish.

### B1. Check Python
```
python3 --version
```
You need 3.10 or newer. If you get "not found": on Mac run `brew install python` (install Homebrew first from https://brew.sh if needed); on Ubuntu/WSL run `sudo apt update && sudo apt install -y python3 python3-venv`.

### B2. Install uv (installs Python packages fast)
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Close the terminal, open it again, and check with `uv --version`.

### B3. Install the AWS CLI
Mac: `brew install awscli`
Ubuntu/WSL:
```
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip && unzip awscliv2.zip && sudo ./aws/install
```
Check: `aws --version`

### B4. Tell the AWS CLI who you are
```
aws configure
```
It asks four questions. Paste AWS_ACCESS_KEY_ID, then AWS_SECRET_ACCESS_KEY, then type `us-east-1`, then type `json`.
Check it works:
```
aws sts get-caller-identity
```
You should see your account number. If you see an error, run `aws configure` again and paste carefully.

### B5. Install the SAM CLI (deploys the backend in one command)
Mac: `brew install aws-sam-cli`
Ubuntu/WSL: `pip install aws-sam-cli` (if pip is missing: `sudo apt install -y python3-pip`)
Check: `sam --version`

### B6. Install make and zip if missing
Mac: already there (if `make` says "command not found", run `xcode-select --install`).
Ubuntu/WSL: `sudo apt install -y make zip`

---

## Part C: get the code running on your laptop (about 20 minutes)

### C1. Get the folder
Copy the `ghanti` folder onto your laptop (from Jay, or from the repo once it is pushed). Open a terminal inside it:
```
cd path/to/ghanti
```

### C2. Create your settings file
```
cp .env.example .env
```
Open `.env` in any text editor and fill in these lines from your notes:
```
OPENAQ_API_KEY=...
TELEGRAM_BOT_TOKEN=...
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
COORDINATOR_CHAT_ID=...
TEACHER_CHAT_ID=...
SMS_NUMBERS=+91...,+91...
AWS_DEFAULT_REGION=us-east-1
```
Leave the three TABLE lines and PUBLIC_BASE_URL empty for now. Never share this file or commit it to git; it is already in .gitignore.

### C3. Install and test
```
make setup
make test
```
You should see `Ran 13 tests ... OK`.

### C4. See it work with real air data (no AWS needed)
```
make local
```
You should see tomorrow's hourly forecast for the seed school and one call per slot. If it fails with a network error, run it again.

### C5. Put in your real school
Open `backend/scripts/seed_school.py` in an editor. Change:
- `name` and `city`
- `lat` and `lon`: open Google Maps, right-click the school, click the numbers that appear to copy them; the first is lat, the second is lon.
- the `slots`: match the real timetable photo (times, minutes, how many children, how hard they run: light, moderate or vigorous, the youngest age).
- `weekdays`: include `"sat"` for anything that happens on Saturday.
- `move_windows`: the times the ground is free for a moved slot.
Save. Run `make local` again to see calls for your real slots.

---

## Part D: put the backend on AWS (about 40 minutes)

### D1. Deploy
```
make deploy
```
The first time, it asks questions. Answer:
- Stack Name: `ghanti`
- AWS Region: `us-east-1`
- Confirm changes before deploy: `N`
- Allow SAM CLI IAM role creation: `Y`
- Disable rollback: `N`
- ApiFunction Function Url may not have authorization defined, Is this okay?: `y`
- Save arguments to configuration file: `Y`, then press Enter for the defaults.
Wait 3 to 5 minutes. The end shows a table called Outputs.

### D2. Copy the outputs into your settings
```
make outputs
```
You see four values. Put three into `.env`:
```
SCHOOLS_TABLE=...   (the SchoolsTableName value)
CALLS_TABLE=...     (CallsTableName)
READINGS_TABLE=...  (ReadingsTableName)
```
Copy the ApiUrl value. Open `frontend/index.html`, find the line near the top that says `const API_BASE = "PASTE_FUNCTION_URL_HERE";` and paste the URL between the quotes, without the final slash.

### D3. Load your school and start recording air
```
make seed
make record
```
`seed` should say "seeded demo-school into ...". `record` should print the station's name and a number of rows. If it says no station within 15 km, open `backend/ghanti/station.py`, change `radius_m=15000` to `radius_m=30000`, and run `make record` again.

From now on the recorder runs by itself every hour on AWS.

### D4. The first real call
At 6 PM today the plan runs by itself. If it is already past 6 PM, run it now:
```
make plan
```
Both Telegram chats should receive the message with a button. Open `frontend/index.html` by double-clicking it; the Tomorrow view should show the same calls.

If Telegram got nothing: in a browser open `https://api.telegram.org/botTOKEN/sendMessage?chat_id=YOURID&text=hi` (fill in TOKEN and YOURID). If that fails, the id or token is wrong.

---

## Part E: put the website on AWS (Saturday morning, about 30 minutes)

### E1. Make the zip
```
make frontend-zip
```
This creates `frontend.zip`.

### E2. Amplify
1. AWS search bar: Amplify, open AWS Amplify. Click Create new app (or Deploy an app).
2. Choose "Deploy without Git". App name: `ghanti`. Branch name: `main`.
3. Drag `frontend.zip` into the upload box. Save and deploy.
4. In a minute you get an address like `https://main.xxxxx.amplifyapp.com`. Open it on your phone. The Tomorrow view should load.

### E3. Tell the backend the website address
Put the address into `.env` as `PUBLIC_BASE_URL=https://main.xxxxx.amplifyapp.com` and run:
```
make deploy
```
Tonight's teacher links will now open the live website.

### E4. Every time you change index.html
Run `make frontend-zip` and upload the new zip in Amplify (open the app, the branch, "Deploy updates").

---

## Part F: Saturday checks (what runs by itself, and what you screenshot)

- 6:10 AM: the re-check runs on AWS. Telegram may show an "Updated" message. Screenshot it either way. To run it yourself: `make recheck`.
- Morning: on the teacher phone, open the Telegram link, tap Can't on one slot, pick a reason. Record the screen. The coordinator chat shows the change.
- 3:00 PM: the verify step runs on AWS and the ledger fills. Screenshot the Tomorrow view's ledger table. To run it yourself: `make verify`.
- Afternoon: `make replay` to fill the Replay page. Then open the website on a phone and a laptop and click every view once.
- Fill the brackets in README.md so the status table says exactly what ran.
- Stop adding things at 8 PM.

---

## Part G: Sunday (record and submit)

1. Record the video with the script in EXECUTION.md section 3. Under three minutes. Show the AWS console screens (Lambda, DynamoDB, EventBridge Scheduler, Bedrock, Amplify) so AWS is visible.
2. Upload to YouTube.
3. Make the GitHub repo public. Before pushing, check `.env` is not inside it (`git status` should not list `.env`).
4. Submit: video link, the Amplify address, the repo link.

---

## If you get stuck

- Any command says "command not found": the tool from Part B is not installed, or you need to close and reopen the terminal.
- `make deploy` fails mentioning ScheduleV2: `pip install --upgrade aws-sam-cli` and try again.
- `make plan` says `'used_model': False`: Bedrock did not answer, the template text was used. The product still works; check A5 later.
- `make record` says 401: the OpenAQ key is missing from `.env`.
- Nothing arrives on Telegram: the person never pressed Start on the bot, or the chat id is wrong.
- The website says "Is API_BASE set?": you have not pasted the ApiUrl into index.html, or you kept the trailing slash.
