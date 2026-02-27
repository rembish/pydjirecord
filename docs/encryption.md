# Encryption

DJI flight logs use different encryption schemes depending on the format version:

| Version | Encryption | Details |
|---------|-----------|---------|
| 1–6     | None | Records are stored as plain binary data |
| 7–12    | XOR | CRC64-derived 8-byte key per record type |
| 13–14   | XOR + AES-256-CBC | XOR decoding followed by AES decryption with per-feature-point keys fetched from the DJI API |

## XOR encoding (v7–12)

Each record is XOR-encoded with an 8-byte key derived from the record's magic byte and the CRC64 polynomial (Jones bit-reversed variant). The key derivation is deterministic — no external keys are needed.

## AES encryption (v13–14)

In addition to XOR encoding, records are encrypted with AES-256-CBC. Each record type maps to a *feature point*, and each feature point has its own AES key and IV. These keys are fetched from the DJI API at:

```
https://dev.dji.com/openapi/v1/flight-records/keychains
```

The encrypted key material is stored in `KeyStorage` records within the log file itself. The API decrypts and returns the actual AES keys.

After each record is decrypted, the IV is updated (IV chaining) so that consecutive records of the same type use different IVs.

A [DJI API key](guide/api-key.md) is required for v13+ log decryption.
