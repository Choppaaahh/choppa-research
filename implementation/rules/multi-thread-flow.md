# Multi-Thread Flow — Act, Don't Queue

The default operating mode is multiple threads active simultaneously. Bot running + experiments firing + model training + research sweeping + builds shipping. This is normal, not "busy."

## Rules

1. **"Fix X" = fix X now.** Don't defer because other threads are active. Don't offer workarounds. The fix takes 2 minutes. The workaround costs confusion on every read.

2. **User context shifts don't pause agent tasks.** User stepping away doesn't mean stop working. It means: keep things running, fix what needs fixing, check on running processes.

3. **Never deprioritize a direct instruction because of context.** "Fix the output" during a busy session = fix the output. Not "I'll note that for later." The whole point of the scaffold is handling multiple threads.

4. **Acknowledge + act, not acknowledge + defer.** Bad: "Got it, I'll note that." Good: "Got it, fixing now — [opens file]."

## Why This Exists

An agent deferred a 2-minute code fix because the user had stepped away and another task was running. The user had to ask twice. Multi-thread parallelism is the operating mode — deferring because "it's busy" is the opposite of what the system is built for.

The scaffold exists to absorb parallelism, not to serialize it.
