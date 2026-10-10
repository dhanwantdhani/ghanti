# Ghanti video: shot list (3:00, product on screen by 0:30, AWS visible, data source stated)

Record on Sunday morning in daylight. Screen recordings at 1080p; phone shots with the phone on a desk. Three full takes, pick the best. Speak slowly; 150 words a minute is the ceiling.

```
0:00        0:30        1:00        1:30        2:00        2:30   3:00
|-- hook --|-- live --|-- phone --|-- track --|-- try --|-- AWS --|-end-|
  smog week   plan      teacher     record     sandbox   console   card
```

| Time | What is on screen | Where it comes from | What you say |
|---|---|---|---|
| 0:00-0:10 | The header: "Should the children go outside tomorrow?" then the three numbered steps | Live site, `/#/`, top of page, zoom 125% | "Every morning, four hundred children stand outside for assembly. In a Delhi winter, that is the dirtiest hour of the school day. Nobody at a school looks at air by the hour." |
| 0:10-0:30 | `/#/replay`: scroll to Wednesday 12 November. The one-sentence summary, the orange hour band, then the rows: Morning assembly "Move to 13:20", PE Class 2B "Stay indoors", Recess "Stay indoors". The REPLAY tag is visible | Live site | "Same school, same rules, run on a real November week. Assembly moves to twenty past one. Junior PE stays indoors. The tag says replay, because it is." |
| 0:30-0:45 | `/#/`: The Plan card ("Next school day: Monday, 12 October", the summary sentence, the hour band), then the five rows: four "Go outdoors", one "Outdoors, keep it short" | Live site | "Tonight's real call. The air is fine this week, so four periods go ahead and one is kept short. Ghanti says so rather than inventing a problem." |
| 0:45-1:10 | Deepanshu's phone: the Telegram message arrives, he taps the link, the teacher page opens with the rows and two buttons, he taps OK on one period, Can't on PE 2B, picks "I am teaching another class then"; Dhanashree's Telegram shows the coordinator message | Phone screen recording, done once on Saturday or Sunday from the Monday message | "The teacher gets it on Telegram. OK, or Can't, with a reason. Only that period re-plans, and the coordinator is told." |
| 1:10-1:35 | `/#/` Track record: "5 of 5 calls were right", the table with Forecast, Measured, Right? | Live site, after Saturday 15:05 | "Every afternoon it checks the government monitor one kilometre away. Forecast said this. The monitor measured that. The call was right, or wrong, and it says which. No other air app keeps score on itself." |
| 1:35-1:55 | `/#/try`: steps 1 to 4 visible, click "Use a smog day: 12 Nov 2025", click "Get the call", the rows appear; click "Teacher can't do 13:20" on the moved period and watch the row change | Live site | "Any school. Put in your location and your periods, pick a day. Tell it the teacher can't do that hour, and it re-plans in front of you." |
| 1:55-2:30 | AWS console, Mumbai region: EventBridge Scheduler (4 schedules), Lambda (5 functions), DynamoDB (3 tables), Bedrock model catalog with Nova Lite, Amplify app. Then back to `/#/`, expand "How this call was made" to show the agent trace | Console screen recording, then live site | "Four schedules in Indian time run four Lambdas. DynamoDB holds the calls and the hourly readings. A Strands agent on Amazon Nova fetches the forecast, asks the rules, and writes the opening of the message; it cannot change a call. Amplify serves the page. One SAM template builds all of it." |
| 2:30-2:50 | `/#/`, expand "Where the data comes from"; show the station name, distance, and the last-reported time | Live site | "Forecast from a 45-kilometre model, said on screen. Station name, distance, and the age of its last reading, on screen. The rules are a Python file with fourteen tests." |
| 2:50-3:00 | End card: Ghanti, the live URL, the repo URL | A plain slide | "Ghanti. One school, one teacher, one call a day." |

## Before recording

- Hard-refresh the site and open every view once; the smog week takes a few seconds to compute, open it before the take.
- Set the browser zoom to 125% so the rows are readable at 1080p; the home page should show the header, the three steps and the start of The Plan without scrolling.
- Expand "Hour-by-hour picture" only if there is time left; the rows are the story.
- Close other tabs; hide the bookmarks bar.
- Have the phone recording ready as a file; the teacher link is the one in the Monday message, and the taps only work once per period, so record the first time.
- Time the narration with a stopwatch; cut words until it is under 2:55.

## Upload

YouTube, title "Ghanti: tomorrow's outdoor call for one school (Environmental Hacks 2026)". Description: live URL, repo URL, one line on data sources, one line saying the timetable is illustrative and the replay is modelled air.
