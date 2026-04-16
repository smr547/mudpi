# Enrolling a new human peer with `enroll_peer.py`

From the repo root:

```bash
python3 wireguard/enroll_peer.py james-laptop
```

This will:

- find `james-laptop` in `./wireguard/registry.yaml`
- create the directory named by `key_ref`
- generate:
  - `private.key`
  - `public.key`
  - `preshared.key`
- update the registry entry to:
  - `key_status: existing`
  - `enrollment_status: complete`

Then generate configs:

```bash
python3 wireguard/generate_wg.py
```

That should produce:

```text
wireguard/generated/wg0.conf
wireguard/generated/clients/james-laptop.conf
```

If you need to deliberately replace James's keys:

```bash
python3 wireguard/enroll_peer.py james-laptop --force
```

Be careful: changing keys means the old client config will stop working and must be replaced.
