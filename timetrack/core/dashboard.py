# project/timetrack/core/dashboard.py
"""Dashboard generation for the timetrack application.

Builds a self-contained ``index.html`` from the local time log. The file
inlines all CSS and JS (no CDN, no external requests) so it can be deployed
to any static host and opened from anywhere. Data is embedded as plaintext
JSON, or AES-GCM encrypted when a passphrase is supplied.
"""

import base64
import json
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .storage import Storage


def _build_payload(storage: Storage, days: int = 30) -> dict:
    """Aggregate the log into a dashboard payload.

    Args:
        storage: The Storage instance for persistence.
        days: Number of trailing days to include.

    Returns:
        A serializable dict with summary, daily, activities and entries.
    """
    log = storage.read_log()
    end = date.today()
    start = end - timedelta(days=days - 1)

    daily: Dict[str, float] = {}
    activity: Dict[str, float] = {}
    entries: List[dict] = []

    for entry in log.entries:
        entry_date = entry.start_time.date()
        if start <= entry_date <= end:
            date_str = entry_date.strftime("%Y-%m-%d")
            hours = entry.duration_minutes / 60
            daily[date_str] = daily.get(date_str, 0.0) + hours
            activity[entry.activity] = activity.get(entry.activity, 0.0) + hours
            entries.append(
                {
                    "activity": entry.activity,
                    "start": entry.start_time.strftime("%Y-%m-%d %H:%M"),
                    "end": entry.end_time.strftime("%Y-%m-%d %H:%M"),
                    "hours": round(hours, 2),
                    "notes": entry.notes,
                }
            )

    if daily:
        total_hours = sum(daily.values())
        summary = {
            "total_hours": round(total_hours, 1),
            "avg_per_day": round(total_hours / len(daily), 1),
            "days_tracked": len(daily),
            "activities": len(activity),
        }
    else:
        summary = {
            "total_hours": 0.0,
            "avg_per_day": 0.0,
            "days_tracked": 0,
            "activities": 0,
        }

    daily_list = [
        {"date": d, "hours": round(h, 2)}
        for d, h in sorted(daily.items())
    ]
    activity_list = [
        {"name": a, "hours": round(h, 2)}
        for a, h in sorted(activity.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "days": days,
        "summary": summary,
        "daily": daily_list,
        "activities": activity_list,
        "entries": entries,
    }


def _encrypt_payload(payload: dict, passphrase: str) -> dict:
    """Encrypt the payload with AES-GCM using a PBKDF2-derived key.

    Args:
        payload: The dashboard payload dict.
        passphrase: The user passphrase.

    Returns:
        A dict with base64 salt, iv and ciphertext.

    Raises:
        RuntimeError: if the `cryptography` package is not installed.
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
    except ImportError:
        raise RuntimeError(
            "Passphrase protection requires the 'cryptography' package. "
            "Install it with: pip install cryptography"
        )

    salt = secrets.token_bytes(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100_000)
    key = kdf.derive(passphrase.encode())
    iv = secrets.token_bytes(12)
    aes = AESGCM(key)
    plaintext = json.dumps(payload).encode()
    ciphertext = aes.encrypt(iv, plaintext, None)
    return {
        "salt": base64.b64encode(salt).decode(),
        "iv": base64.b64encode(iv).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
    }


def _render_html(payload: Optional[dict], enc: Optional[dict]) -> str:
    """Render the self-contained dashboard HTML.

    Args:
        payload: Plaintext payload (when not encrypted).
        enc: Encrypted payload (when passphrase protected).

    Returns:
        The full HTML document as a string.
    """
    if enc is not None:
        source = (
            "<script>const ENC = "
            + json.dumps(enc)
            + ";</script>\n"
            + _DECRYPT_SCRIPT
        )
    else:
        source = (
            "<script>const DATA = "
            + json.dumps(payload)
            + ";\nrender(DATA);</script>"
        )

    return _HTML_TEMPLATE.replace("__SOURCE__", source)


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>track — time review</title>
<style>
  :root { --bg:#0f1115; --card:#171a21; --fg:#e6e8ec; --muted:#8b93a1; --accent:#6ee7b7; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  .wrap { max-width:860px; margin:0 auto; padding:32px 20px 64px; }
  h1 { font-size:22px; margin:0 0 4px; }
  .gen { color:var(--muted); font-size:13px; margin-bottom:24px; }
  .stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:14px; margin-bottom:32px; }
  .stat { background:var(--card); border-radius:10px; padding:16px; }
  .stat .v { font-size:24px; font-weight:700; color:var(--accent); }
  .stat .l { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.05em; }
  h2 { font-size:15px; color:var(--muted); margin:28px 0 12px; text-transform:uppercase; letter-spacing:.05em; }
  .row { display:flex; align-items:center; gap:12px; margin:6px 0; }
  .row .name { width:160px; flex:none; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .bar { flex:1; height:14px; background:var(--card); border-radius:7px; overflow:hidden; }
  .bar > span { display:block; height:100%; background:var(--accent); border-radius:7px; }
  .row .h { width:64px; flex:none; text-align:right; color:var(--muted); font-variant-numeric:tabular-nums; }
  table { width:100%; border-collapse:collapse; margin-top:8px; }
  th,td { text-align:left; padding:8px 10px; border-bottom:1px solid #232732; font-size:13px; }
  th { color:var(--muted); font-weight:600; text-transform:uppercase; font-size:11px; letter-spacing:.05em; }
  td.num { text-align:right; font-variant-numeric:tabular-nums; color:var(--muted); }
  .empty { color:var(--muted); }
</style>
</head>
<body>
<div class="wrap">
  <h1>Time Review</h1>
  <div class="gen" id="gen"></div>
  <div id="app"></div>
</div>
<script>
function render(data){
  document.getElementById('gen').textContent = 'Generated ' + data.generated_at + ' — last ' + data.days + ' days';
  var s = data.summary;
  var stats = [
    ['Total hours', s.total_hours + 'h'],
    ['Avg / day', s.avg_per_day + 'h'],
    ['Days tracked', s.days_tracked],
    ['Activities', s.activities]
  ];
  var html = '<div class="stats">';
  stats.forEach(function(st){ html += '<div class="stat"><div class="v">'+st[1]+'</div><div class="l">'+st[0]+'</div></div>'; });
  html += '</div>';

  if (!data.daily.length) {
    html += '<p class="empty">No entries in this period.</p>';
  } else {
    var maxD = Math.max.apply(null, data.daily.map(function(d){return d.hours;}));
    var maxA = Math.max.apply(null, data.activities.map(function(d){return d.hours;}));
    html += '<h2>Daily hours</h2>';
    data.daily.forEach(function(d){
      var pct = maxD ? (d.hours/maxD*100) : 0;
      html += row(d.date, pct, d.hours.toFixed(1)+'h');
    });
    html += '<h2>By activity</h2>';
    data.activities.forEach(function(a){
      var pct = maxA ? (a.hours/maxA*100) : 0;
      html += row(a.name, pct, a.hours.toFixed(1)+'h');
    });
    if (data.entries.length) {
      html += '<h2>Recent entries</h2><table><thead><tr><th>Activity</th><th>Start</th><th>End</th><th class="num">Hours</th></tr></thead><tbody>';
      data.entries.slice().reverse().slice(0,20).forEach(function(e){
        html += '<tr><td>'+esc(e.activity)+'</td><td>'+esc(e.start)+'</td><td>'+esc(e.end)+'</td><td class="num">'+e.hours+'</td></tr>';
      });
      html += '</tbody></table>';
    }
  }
  document.getElementById('app').innerHTML = html;
}
function row(name, pct, label){
  return '<div class="row"><div class="name">'+esc(name)+'</div><div class="bar"><span style="width:'+pct.toFixed(1)+'%"></span></div><div class="h">'+label+'</div></div>';
}
function esc(s){ return String(s).replace(/[&<>]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]; }); }
__SOURCE__
</script>
</body>
</html>"""

_DECRYPT_SCRIPT = """<script>
function b64dec(b){ var s=atob(b); var u=new Uint8Array(s.length); for(var i=0;i<s.length;i++) u[i]=s.charCodeAt(i); return u; }
function deriveKey(pass, salt){
  return crypto.subtle.importKey('raw', new TextEncoder().encode(pass), 'PBKDF2', false, ['deriveKey'])
    .then(function(k){ return crypto.subtle.deriveKey(
      {name:'PBKDF2', salt:salt, iterations:100000, hash:'SHA-256'},
      k, {name:'AES-GCM', length:256}, false, ['decrypt']); });
}
function decrypt(enc, pass){
  var salt=b64dec(enc.salt), iv=b64dec(enc.iv), ct=b64dec(enc.ciphertext);
  return deriveKey(pass, salt).then(function(key){
    return crypto.subtle.decrypt({name:'AES-GCM', iv:iv}, key, ct);
  }).then(function(pt){ return JSON.parse(new TextDecoder().decode(pt)); });
}
(function(){
  var pass = prompt('Passphrase to view your dashboard:');
  if(!pass){ document.getElementById('app').innerHTML='<p class="empty">Passphrase required.</p>'; return; }
  decrypt(ENC, pass).then(function(data){ render(data); })
    .catch(function(){ document.getElementById('app').innerHTML='<p class="empty">Wrong passphrase or corrupted data.</p>'; });
})();
</script>"""


class DashboardManager:
    """Builds the self-contained dashboard HTML from local data."""

    def __init__(self, storage: Storage):
        self.storage = storage

    def generate(
        self,
        output_dir: Path,
        days: int = 30,
        passphrase: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Generate ``index.html`` into ``output_dir``.

        Args:
            output_dir: Directory to write ``index.html`` into.
            days: Number of trailing days to include.
            passphrase: If set, encrypt the embedded data (AES-GCM).

        Returns:
            A tuple of (success, message/path).
        """
        payload = _build_payload(self.storage, days)
        try:
            if passphrase:
                enc = _encrypt_payload(payload, passphrase)
                html = _render_html(None, enc)
            else:
                html = _render_html(payload, None)
        except RuntimeError as e:
            return False, str(e)

        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "index.html"
        path.write_text(html)
        return True, str(path)
