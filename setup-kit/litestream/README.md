# OpenSpace skill DB sync via Litestream + Supabase Storage

Streams the local SQLite skill DB to your Supabase Storage bucket continuously,
so any device that runs `install.sh` ends up sharing the same evolution history.

## How it works

- **Litestream** watches the SQLite WAL and ships changes to S3-compatible storage
  every ~10 seconds. Zero downtime, no schema changes to OpenSpace.
- **Supabase Storage** exposes an S3-compatible endpoint per project, so litestream
  treats it like AWS S3. No Postgres tables involved — pure object storage.
- **Per-device prefix** (`skills/<hostname>/`) — each machine writes to its own
  path so they don't fight over the same WAL. To unify, you periodically download
  one device's snapshot to another (see "Cross-device sync" below).

## Setup

### 1. One-time Supabase prep

In the Supabase dashboard for project `openspace-sync`:

1. **Storage** → **New Bucket** → name: `openspace-db`, **private**
2. **Storage** → **S3 Connection** → **Generate new credentials**
   - Copy the `access key ID` and `secret access key` immediately (shown once)
3. Note your **project ref** (in the URL: `https://supabase.com/dashboard/project/<REF>`)

### 2. Per-device install

```bash
cd ~/OpenSpace-kit/setup-kit
bash litestream/install.sh
# enter project ref, region, S3 keys when prompted
```

Done. Litestream now runs as a background service (launchd on macOS, systemd-user on Linux).

## Cross-device sync

The default config keeps one replica per device (safest — no write conflicts).
To pull another device's evolution into a new machine:

```bash
# pull device "macbook" snapshot to current device
DEVICE_ID=macbook litestream restore \
  -config ~/.openspace/litestream.yml \
  -o /tmp/imported.db \
  ~/OpenSpace/.openspace/openspace.db
# then merge or swap into place while openspace-mcp is stopped
```

For most people, **single-writer-at-a-time** is fine: do heavy work on your laptop
during the day; restore to your desktop when you switch.

## Cost

- Supabase project: **$10/mo** (Pro tier — already approved)
- Storage: skill DBs are tiny (~5 MB after months of use). Storage cost ≈ $0.
- Egress: <1 MB/day. Free tier covers it.

## Disable / uninstall

```bash
# macOS
launchctl unload ~/Library/LaunchAgents/cloud.openspace.litestream.plist
rm ~/Library/LaunchAgents/cloud.openspace.litestream.plist
# Linux
systemctl --user disable --now openspace-litestream.service
rm ~/.config/systemd/user/openspace-litestream.service
```

Local OpenSpace keeps working — only the cloud replica stops.
