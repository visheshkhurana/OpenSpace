# Your openspace-sync Supabase project

Auto-generated. Use these values when running `install.sh`.

| Field          | Value                                |
|----------------|--------------------------------------|
| Project ref    | `fhrynagbidbznfvuoxcn`               |
| Region         | `ap-south-1`                         |
| S3 endpoint    | `https://fhrynagbidbznfvuoxcn.storage.supabase.co/storage/v1/s3` |
| Bucket         | `openspace-db` (private, 1 GB cap)   |
| Dashboard      | https://supabase.com/dashboard/project/fhrynagbidbznfvuoxcn |

## Status: VERIFIED end-to-end (2026-04-20)

A full snapshot + WAL replication + restore round-trip was tested against this
bucket using your S3 keys. Pipeline confirmed working. `force-path-style: true`
is required for Supabase — baked into `litestream.yml`.

## Credential storage

The S3 keys are stored on each device at `~/.openspace/litestream.env` (chmod 600).
They are **not** committed to git. To rotate, generate new keys at
https://supabase.com/dashboard/project/fhrynagbidbznfvuoxcn/storage/s3 and re-run
`install.sh`.
