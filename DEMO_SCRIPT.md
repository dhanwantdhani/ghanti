# Ghanti demo script (2:50)

One take of the browser, one phone recording, one console recording, one end card. Narrate over the browser take; the phone and console clips are cut in. Read at a walking pace; every line below fits its slot at 140 words a minute.

```
0:00   0:12        0:35        0:55       1:20      1:40       2:05        2:35    2:50  3:00
|hook |  smog day  | tonight   |  phone   | score   |  try it  |  AWS       | data  | end |
 home   #/replay     #/           clip      #/         #/try      console+     #/      card
                                                                 trace
```

Browser at 125% zoom, bookmarks bar hidden, only one tab. Open `#/replay` once before recording so it is cached.

---

## 0:00 Hook (12 s)

**Screen:** `https://main.d3brqy16xi3d2g.amplifyapp.com/` top of page. Do not scroll. The question and the three steps are visible.

**Say:** "Ten to eight, morning assembly, four hundred children outside. On a November day at this school: one hundred and twelve micrograms at eight, sixty-nine at one. Same day. Ghanti moves the period."

## 0:12 The smog day (23 s)

**Navigate:** click **A smog week** in the nav. Scroll past the tiles to **Wednesday, 12 November**. Stop with the hour band and the first three rows in frame.

**Point at:** the orange band (112, 112, 108), then the rows in order. Say the number on each row as you point at it.

**Say:** "Here is that day, period by period. Assembly: one hundred and twelve, Poor. It moves to twenty past one, where it is sixty-nine. Junior PE at half past eight, thirty-eight seven-year-olds: one hundred and ten, indoors. Recess: ninety-two, indoors. Senior PE: eighty-seven, outdoors but kept short. Every number and every reason is on the row."

## 0:35 Tonight's real call (20 s)

**Navigate:** click **Tomorrow's plan**. Scroll until **The Plan** card is at the top. Pause two seconds on the summary sentence, then scroll to the five rows.

**Say:** "This is live. Monday's plan went to the teacher at six this evening. Assembly: seventy-three, Moderate, go outdoors. PE for seven-year-olds: sixty-six, kept short, because under-tens get the stricter rule. The other three are in the fifties. When the numbers are fine, Ghanti says so."

Read the numbers off the screen at recording time; the 6:10 AM re-check can change them.

## 0:55 The teacher's phone (25 s)

**Cut to:** the phone recording. Telegram message arrives; do not hold on it. Tap the link within two seconds, so what judges read is the teacher page, not the message text. The teacher page opens, tap **OK, will do** on Morning assembly, tap **Can't** on PE Class 2B, tap **I am teaching another class then**. Cut to the coordinator's Telegram showing the message.

**Say:** "The teacher gets it on Telegram. He opens the link, taps OK, or Can't with a reason. Only that period is re-planned, and the coordinator is told within a second. No app to install, no login."

## 1:20 The score (20 s)

**Navigate:** back in the browser, scroll to **Track record**. The headline **5 of 5 calls were right** and the table with Forecast and Measured columns.

**Point at:** one row, forecast number then measured number.

**Say:** "Every afternoon at three, Ghanti checks the government monitor one kilometre from the school. Forecast said fifty-three; the monitor measured sixty-three; the call was still right. It keeps score on itself, in public."

## 1:40 Try it (25 s)

**Navigate:** click **Try your school**. Click **Use a smog day: 12 Nov 2025**. Click **Get the call**. The page scrolls to the rows. Click **Teacher can't do 13:20** on the first row and let the rows redraw.

**Say:** "Any school can try it. Pick a day. Here is the same smog day. Now the teacher says he can't do twenty past one, and the plan redoes itself in front of you, using the next free hour."

## 2:05 Built on AWS (30 s)

**Cut to:** console recording, Mumbai region, in this order, four to five seconds each: **EventBridge Scheduler** (four schedules), **Lambda** (five functions), **DynamoDB** (three tables), **Bedrock** model catalog on Nova Lite, **Amplify** app. Then cut back to the browser on `#/`, scroll to **What the teacher received**, click **How this call was made** to open the trace.

**Say:** "Four schedules in Indian time run four Lambdas. DynamoDB keeps every call and every hourly reading. A Strands agent on Amazon Nova fetches the forecast, asks the rules, and writes the opening of the message. It cannot change a call, and the trace shows exactly what it did. Amplify serves the page. One SAM template builds all of it."

## 2:35 Where the numbers come from (15 s)

**Navigate:** scroll to the bottom, click **Where the data comes from**.

**Say:** "Forecast from a forty-five kilometre model, said on screen. Station name, distance, and the age of its last reading, on screen. The rules are one Python file with fourteen tests."

## 2:50 End card (10 s)

**Screen:** plain slide: Ghanti, the live URL, the repo URL.

**Say:** "Ghanti. One school, one teacher, one call a day."

---

## Cuts that keep it under three minutes

If the take runs long, drop in this order: the "No app to install, no login" line, the last sentence of the AWS segment, the hour-band pointing in the smog day.

## Things that go wrong

- The smog week takes three to four seconds to compute. Open it before recording.
- Teacher taps work once per period. Record the phone the first time. The message to use is the one sent Sunday 6 PM for Monday; the Saturday one was replaced.
- Numbers, not adjectives. Say "one hundred and twelve, Poor", not "very bad air". Every figure in this script is on screen at the moment it is said.
- Sunday has no periods, so the home page shows Monday. That is correct; the headline says "Next school day".
- If a row says "Updated at 6 AM", say "the morning re-check changed it"; that is a feature.
