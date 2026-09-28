# Long-running agent work runs on Temporal

Chasing a stalled Application can mean waiting 14 days, nudging an official, waiting for human approval, and retrying, all while surviving deploys and restarts. Temporal is built for exactly this. A Postgres job queue with cron would need all of that rebuilt by hand, and agent frameworks such as LangGraph focus on reasoning, not durable waiting. The agent reasoning loop itself stays a small loop we write ourselves.
