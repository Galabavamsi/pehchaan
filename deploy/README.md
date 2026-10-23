# Deploying the demo (`api.humanslop.in`, `demo.humanslop.in`)

One EC2 box in **ap-south-1** runs everything with Docker Compose:

| Service | What | Exposed |
|---|---|---|
| `caddy` | TLS (Let's Encrypt) for both hosts; serves the built web demo | 80, 443 |
| `api` | Risk API (`app/server` + `engine`), SQLite + signing key on a volume | via Caddy |
| `voice` | Voice Provenance Service v1, CPU int8 (shadow mode: never changes a decision) | internal only |

No keys go on the box: `.env` (Vobiz, Sarvam, …) stays on the laptop, and `push.sh` only sends git-tracked files.
Real calls (`ml/realcall`) keep running from the laptop.

## Current deployment (20 Oct 2026)

| What | Value |
|---|---|
| Instance | `i-00b0303d996932d12` `pehchaan-demo`, c7i.large, Ubuntu 24.04, ap-south-1, 30 GB gp3 |
| Elastic IP | `3.109.40.69` |
| Security group | `sg-024e0128fd2099f26` `pehchaan-demo` (80/443 public, 22 from 103.147.138.252/32) |
| Key pair | `pehchaan-ml` (imported into ap-south-1; private key `ml/infra/pehchaan-ml`) |
| Role | `pehchaan-ml-ec2` (pehchaan buckets only) |
| Budget | `pehchaan-monthly` $150, tag `Project=pehchaan`, before credits; mails Varun at 50/80 % actual, 100 % forecast |

SSH alias on Varun's laptop (`~/.ssh/config`): `pehchaan-demo`. If your IP changes, update port 22 on the SG.

## One-time set-up (how the box above was made)

1. **Instance:** Ubuntu 24.04, `c7i.large` (2 vCPU, 4 GB): voice uses ~1.05 GB RAM, API ~90 MB. 30 GB gp3,
   instance profile `pehchaan-ml-ec2`, IMDSv2, tag `Project=pehchaan`, user-data `deploy/user_data.sh`
   (Docker, AWS CLI, 2 GB swap, v1 weights from S3 into `~/pehchaan/deploy/weights`).
2. **Security group** `pehchaan-demo`: 80 and 443 from anywhere; 22 from your current IP only.
3. **Elastic IP** so the address survives a stop/start.
4. **DNS (Cloudflare, `humanslop.in`):** two A records, `api` and `demo` → the Elastic IP, **DNS only (grey cloud)**
   so Caddy can get certificates. Don't touch any other record (jalsakshi, charter, urumi, mail).
5. On the laptop: `cp deploy/env.deploy.example deploy/.env.deploy` and add an SSH alias `pehchaan-demo`.

## Deploy / redeploy

```bash
bash deploy/push.sh pehchaan-demo
```

It builds `app/web` with `VITE_API=https://$API_HOST`, ships the code and the web build, and runs
`docker compose up -d --build`.

## Check

```bash
curl -s https://api.humanslop.in/v1/health
```

`voice_service` should say `http://voice:8500`. Then, **from a phone on mobile data**, open
`https://demo.humanslop.in/#/relative` and, on the laptop, `https://demo.humanslop.in/#/demo` → T1.

## Local smoke test (no TLS)

```bash
docker compose -f deploy/docker-compose.yml -f deploy/compose.local.yml up --build api voice
```

The API is then on http://127.0.0.1:8400, and the web dev server (`npm run dev`) uses it as usual.

## Notes

- If the voice container is down or slow, the API falls back to its mock score; the demo keeps working.
- Demo endpoints (`/v1/demo/*`) are open by design: every person, bank and UPI ID in them is fictional.
- Stop the instance after the finale (EBS + Elastic IP still cost a little while stopped).
