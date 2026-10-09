# Ghanti. Run "make setup" once, then the others. Secrets come from .env (never committed).

PY = .venv/bin/python
export PYTHONPATH := backend

-include .env
export

.PHONY: setup test local seed replay record plan recheck verify deploy outputs frontend-zip

setup:            ## venv and dependencies with uv
	uv venv .venv
	uv pip install --python $(PY) -r backend/requirements.txt

test:             ## unit tests for the rules and dose arithmetic
	$(PY) -m unittest discover -s backend/tests -t backend

local:            ## real forecast, real rules, templated message; no AWS; under a minute
	$(PY) backend/scripts/dry_run_plan.py

seed:             ## write the live school to DynamoDB (needs SCHOOLS_TABLE in .env)
	$(PY) backend/scripts/seed_school.py

replay:           ## build the labelled replay week and store it (needs CALLS_TABLE in .env)
	$(PY) backend/scripts/make_replay.py

record plan recheck verify:   ## run a handler locally against the deployed tables, e.g. make plan
	$(PY) -c "from handlers.$@ import handler; print(handler())"

deploy:           ## build and deploy the stack; parameters from .env (empty ones fall back to template defaults)
	sam build
	@overrides=""; \
	for pair in "OpenAqApiKey=$(OPENAQ_API_KEY)" "TelegramBotToken=$(TELEGRAM_BOT_TOKEN)" "WaqiToken=$(WAQI_TOKEN)" \
	            "BedrockModelId=$(BEDROCK_MODEL_ID)" "LiveSchoolId=$(LIVE_SCHOOL_ID)" "PublicBaseUrl=$(PUBLIC_BASE_URL)" \
	            "SmsNumbers=$(SMS_NUMBERS)"; do \
	  case "$$pair" in *=) ;; *) overrides="$$overrides $$pair";; esac; \
	done; \
	echo "sam deploy with overrides for: $$(echo $$overrides | sed -E 's/=[^ ]*//g')"; \
	sam deploy --stack-name ghanti --resolve-s3 --capabilities CAPABILITY_IAM \
	  --no-confirm-changeset --no-fail-on-empty-changeset --parameter-overrides $$overrides

outputs:          ## print the stack outputs (API URL, table names) to paste into .env and index.html
	sam list stack-outputs --stack-name ghanti --output json

frontend-zip:     ## zip the frontend for Amplify manual deploy
	cd frontend && zip -r ../frontend.zip index.html
