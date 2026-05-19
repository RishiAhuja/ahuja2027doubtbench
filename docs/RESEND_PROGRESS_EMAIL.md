# Progress Email (Resend)

Send a compact EXP-02 overnight progress summary every 30 minutes.

## Hugging Face token (gated models)

Llama models require a Hugging Face token with accepted license:

```bash
mkdir -p ~/.config/caisc
nano ~/.config/caisc/hf.env
```

```bash
HF_TOKEN=hf_your_token_here
```

The PBS GPU script sources this file automatically.

## 1. Create env file on the cluster (never commit)

```bash
mkdir -p ~/.config/caisc
nano ~/.config/caisc/resend.env
```

```bash
RESEND_API_KEY=re_xxxxxxxx
RESEND_FROM="CAISc HPC <onboarding@resend.dev>"
RESEND_TO=your.email@example.com
```

Use a verified sender domain in Resend if you have one; otherwise use the Resend onboarding address for testing.

## 2. Send one test email

```bash
cd /Data3/it_FA0571/caisc
export PATH=/opt/pbs/bin:$PATH
scripts/email_progress.sh
```

## 3. Start 30-minute watcher (login node)

```bash
cd /Data3/it_FA0571/caisc
nohup bash scripts/watch_progress_email.sh 30 >> logs/progress_email/watch.log 2>&1 &
echo $! > logs/progress_email/watch.pid
```

Stop:

```bash
kill "$(cat logs/progress_email/watch.pid)"
```

## What the email contains

- PBS queue state (running / queued caisc jobs)
- Per-model row counts `done/expected` from `raw_outputs.jsonl`
- Batch-level total percentage
