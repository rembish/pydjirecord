# DJI API key

Logs version 13 and above use AES-256-CBC encryption. To decrypt them you need a DJI API key.

## Obtaining a key

1. Visit [DJI Developer Technologies](https://developer.dji.com/user) and log in.
2. Click **CREATE APP**, choose **Open API** as the App Type, and fill in the required details (App Name, Category, Description).
3. Activate the app through the confirmation link sent to your email.
4. On your developer user page, find your app's details — the ApiKey is labeled as the **SDK key**.

## Providing the key

The key can be provided via:

- `--api-key KEY` CLI argument
- `DJI_API_KEY` environment variable
- `.env` file in the current directory

```bash
# .env file
DJI_API_KEY=your_key_here
```

## Network considerations

Decryption requires fetching per-flight keys from the DJI API over HTTPS.

In **environments with certificate validation issues** (corporate proxies, custom CA stores), `log.fetch_keychains()` may raise a TLS error. Pass `verify=False` or use the `--no-verify` CLI flag to bypass certificate checking. Keychains are cached after the first successful fetch so you only need this once per log file.

In **air-gapped or network-restricted environments** (no outbound HTTPS), `log.fetch_keychains()` will raise a network error. In that case:

- `log.details` (the unencrypted header) is still fully readable.
- `log.version`, `log.details.aircraft_name`, `log.details.start_time`, etc. work without a network call.
- `djirecord flight.txt --json` works without a key and returns a details-only JSON object (no frame data).
- Frame-level telemetry and the frame-bearing export formats (`--raw`, `--csv`, `--geojson`, `--kml`, and `--json` with frames) require the decryption keys.
