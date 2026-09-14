# Module 02: Terminal-First Debugging with cURL & Wire Inspection

## 1. Why cURL is Essential for SDETs
* Zero GUI overhead.
* Available on any remote container, CI runner, or SSH bastion.
* Direct wire-level inspection without browser/Postman abstractions.

---

## 2. Essential Flags Reference

| Flag | Purpose | Production Use Case |
| :--- | :--- | :--- |
| `-v` | Verbose mode | Inspect DNS, TLS handshake, outgoing headers (`>`), incoming headers (`<`) |
| `-i` | Include headers | Quick inspection of status code, `Content-Type`, `ETag`, `X-Request-Id` |
| `-X <METHOD>` | HTTP Verb | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `-H "K: V"` | Custom Header | Set Auth tokens, `Accept`, `Content-Type` |
| `-d '<data>'` | Request Body | Send payload (defaults to POST) |
| `--json '<data>'` | Modern JSON flag | Sets method to `POST`, auto-adds `Content-Type` and `Accept: application/json` |
| `-w "%{http_code}\n"` | Format output | Extract raw status code for CLI assertions |

---

## 3. Windows PowerShell Nuances & Gotchas

### Issue 1: `curl` vs `curl.exe`
In Windows PowerShell (5.1), `curl` is an alias for `Invoke-WebRequest`.
* **Always run `curl.exe`** on Windows to invoke the real binary.

### Issue 2: Quote Escaping in PowerShell
PowerShell parses unescaped double quotes inside strings and splits on spaces.
* Broken: `-d "{"issue": "ATLAS-101", "summary": "Payment timeout"}"` (treats `timeout"` as another argument)
* Working: `curl.exe -v --json '{\"issue\": \"ATLAS-101\", \"summary\": \"Payment timeout\"}' https://httpbin.org/post`

---

## 4. Key Headers on the Wire
* **`Content-Length`**: Exact byte size of the request/response body. Tells the receiver when the payload has finished streaming over the TCP socket.
* **`Connection: keep-alive`**: Instructs the underlying TCP socket to stay open for reuse by subsequent requests (Connection Pooling).
