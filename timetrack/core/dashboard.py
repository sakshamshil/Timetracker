# project/timetrack/core/dashboard.py
"""Dashboard generation for the timetrack application.

Builds a self-contained ``index.html`` from the local time log. The file
inlines all CSS and JS (no CDN, no external requests) so it can be deployed
to any static host and opened from anywhere. Data is embedded as plaintext
JSON, or AES-GCM encrypted when a passphrase is supplied.

Design ("Nightfall"): each day is a luminous ribbon against a dusk gradient;
the most recent day is a glowing 24-hour hero, prior days stack beneath as a
woven strata of time.
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
        A serializable dict with summary, day ribbons, and activities.
    """
    log = storage.read_log()
    end = date.today()
    start = end - timedelta(days=days - 1)

    activity: Dict[str, float] = {}
    # day -> list of segments {start, end, activity} in fractional hours
    ribbons: Dict[str, List[dict]] = {}
    day_totals: Dict[str, float] = {}

    for entry in log.entries:
        entry_date = entry.start_time.date()
        if start <= entry_date <= end:
            ds = entry_date.strftime("%Y-%m-%d")
            hours = entry.duration_minutes / 60
            activity[entry.activity] = activity.get(entry.activity, 0.0) + hours
            day_totals[ds] = day_totals.get(ds, 0.0) + hours
            start_h = entry.start_time.hour + entry.start_time.minute / 60
            end_h = entry.end_time.hour + entry.end_time.minute / 60
            end_h = min(end_h, 24.0)
            ribbons.setdefault(ds, []).append(
                {"start": round(start_h, 2), "end": round(end_h, 2), "activity": entry.activity}
            )

    if day_totals:
        total_hours = sum(day_totals.values())
        summary = {
            "total_hours": round(total_hours, 1),
            "avg_per_day": round(total_hours / len(day_totals), 1),
            "days_tracked": len(day_totals),
            "activities": len(activity),
        }
    else:
        summary = {
            "total_hours": 0.0,
            "avg_per_day": 0.0,
            "days_tracked": 0,
            "activities": 0,
        }

    # Build day ribbons, most recent first.
    day_list = []
    for ds in sorted(ribbons.keys()):
        d = datetime.strptime(ds, "%Y-%m-%d").date()
        now_marker = None
        if d == date.today():
            n = datetime.now()
            now_marker = round(n.hour + n.minute / 60, 2)
        day_list.append(
            {
                "date": ds,
                "weekday": d.strftime("%a"),
                "total_hours": round(day_totals[ds], 1),
                "segments": sorted(ribbons[ds], key=lambda s: s["start"]),
                "now": now_marker,
            }
        )
    day_list.reverse()

    activity_list = [
        {"name": a, "hours": round(h, 2)}
        for a, h in sorted(activity.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "days": days,
        "summary": summary,
        "dayRibbons": day_list,
        "activities": activity_list,
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


_PALETTE = {
    "coding": "#7AA2F7", "code": "#7AA2F7",
    "meetings": "#BB9AF7", "meeting": "#BB9AF7",
    "writing": "#9ECE6A", "write": "#9ECE6A",
    "admin": "#E0AF68", "email": "#E0AF68",
    "learning": "#7DCFFF", "read": "#7DCFFF", "reading": "#7DCFFF",
    "design": "#F7768E",
    "exercise": "#73DACA",
    "rest": "#414868", "break": "#414868", "breaks": "#414868",
    "other": "#565F89",
}


def _color_js() -> str:
    return (
        "var PALETTE=" + json.dumps(_PALETTE) + ";\n"
        "function hashHue(s){var h=0;for(var i=0;i<s.length;i++)h=(h*31+s.charCodeAt(i))%360;return h;}\n"
        "function colorFor(name){var n=(name||'').toLowerCase();if(PALETTE[n])return PALETTE[n];"
        "return 'hsl('+hashHue(name)+',45%,62%)';}\n"
    )


def _render_html(payload: Optional[dict], enc: Optional[dict]) -> str:
    """Render the self-contained dashboard HTML.

    Args:
        payload: Plaintext payload (when not encrypted).
        enc: Encrypted payload (when passphrase protected).

    Returns:
        The full HTML document as a string.
    """
    if enc is not None:
        source = "const ENC = " + json.dumps(enc) + ";\n" + _DECRYPT_BOOTSTRAP
    else:
        source = "const DATA = " + json.dumps(payload) + ";\nrender(DATA);"

    return _HTML_TEMPLATE.replace("__SOURCE__", source).replace("__COLOR__", _color_js())


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>time review</title>
<style>
  :root{
    --bg-top:#1a1730; --bg-bot:#0d0b16;
    --ink:#C8CCF0; --muted:#7C82A8; --faint:#3a3a55;
    --track:#16142a;
  }
  *{box-sizing:border-box}
  html,body{margin:0}
  body{
    min-height:100vh;
    background:linear-gradient(180deg,var(--bg-top),var(--bg-bot));
    color:var(--ink);
    font:15px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    -webkit-font-smoothing:antialiased;
  }
  .mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
  .wrap{max-width:880px;margin:0 auto;padding:40px 22px 72px}
  header{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:34px}
  h1{font-size:19px;font-weight:600;letter-spacing:.01em;margin:0}
  .range{font-size:12px;color:var(--muted)}
  .eyebrow{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);margin:0 0 10px}
  .hero-total{font-size:13px;color:var(--ink);margin:0 0 12px}
  .hero-total b{font-family:ui-monospace,monospace;font-size:22px;font-weight:600;color:#fff}
  .ribbon{position:relative;height:34px;background:var(--track);border-radius:8px;overflow:hidden}
  .ribbon.hero{height:46px;box-shadow:0 0 0 1px rgba(255,255,255,.04),0 8px 30px -12px rgba(122,162,247,.35)}
  .seg{position:absolute;top:0;bottom:0;border-radius:4px;opacity:.92;
       transition:filter .15s ease, opacity .15s ease}
  .seg:hover{filter:brightness(1.25);opacity:1}
  .now{position:absolute;top:-4px;bottom:-4px;width:2px;background:#fff;opacity:.7}
  .ticks{display:flex;justify-content:space-between;margin-top:8px;font-size:10px;color:var(--muted)}
  .strata{margin-top:30px;display:flex;flex-direction:column;gap:6px}
  .row{display:flex;align-items:center;gap:12px}
  .row .lab{width:42px;flex:none;font-size:11px;color:var(--muted)}
  .row .ribbon{height:14px;flex:1}
  .row .tot{width:46px;flex:none;text-align:right;font-size:11px;color:var(--muted)}
  .legend{margin-top:36px}
  .legend .item{display:flex;align-items:center;gap:12px;margin:7px 0}
  .legend .sw{width:10px;height:10px;border-radius:3px;flex:none}
  .legend .nm{width:130px;flex:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .legend .bar{flex:1;height:8px;background:var(--track);border-radius:4px;overflow:hidden}
  .legend .bar>span{display:block;height:100%;border-radius:4px}
  .legend .hr{width:64px;flex:none;text-align:right;font-size:12px;color:var(--muted)}
  .empty{color:var(--muted);margin-top:40px}
  @media (prefers-reduced-motion: no-preference){
    .seg{animation:grow .5s ease both}
    .strata .row{animation:fade .5s ease both}
    @keyframes grow{from{transform:scaleX(0);transform-origin:left}to{transform:scaleX(1)}}
    @keyframes fade{from{opacity:0}to{opacity:1}}
  }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>time review</h1>
    <div class="range mono" id="range"></div>
  </header>
  <div id="app"></div>
</div>
<script>
__COLOR__
function ribbon(segments, opts){
  opts = opts || {};
  var h = '<div class="ribbon'+(opts.hero?' hero':'')+'">';
  segments.forEach(function(s,i){
    var left = s.start/24*100, width = Math.max((s.end-s.start)/24*100, 0.4);
    h += '<div class="seg" style="left:'+left+'%;width:'+width+'%;background:'+colorFor(s.activity)+
         ';animation-delay:'+(i*40)+'ms" title="'+esc(s.activity)+'"></div>';
  });
  if(opts.now!=null){
    h += '<div class="now" style="left:'+(opts.now/24*100)+'%"></div>';
  }
  h += '</div>';
  return h;
}
function render(data){
  document.getElementById('range').textContent = 'last '+data.days+' days';
  if(!data.dayRibbons.length){
    document.getElementById('app').innerHTML = '<p class="empty">No time tracked in this period. '+
      'Run <span class="mono">track start</span> to begin.</p>';
    return;
  }
  var hero = data.dayRibbons[0];
  var html = '';
  html += '<p class="eyebrow">'+hero.weekday+' &middot; '+hero.date+'</p>';
  html += '<p class="hero-total"><b>'+hero.total_hours+'h</b> tracked</p>';
  html += ribbon(hero.segments, {hero:true, now:hero.now});
  html += '<div class="ticks mono"><span>00</span><span>06</span><span>12</span><span>18</span><span>24</span></div>';

  html += '<div class="strata">';
  data.dayRibbons.slice(1).forEach(function(d, i){
    html += '<div class="row" style="animation-delay:'+(i*18)+'ms">'+
      '<div class="lab mono">'+d.weekday+'</div>'+
      ribbon(d.segments, {})+
      '<div class="tot mono">'+d.total_hours+'h</div></div>';
  });
  html += '</div>';

  if(data.activities.length){
    var max = data.activities[0].hours || 1;
    html += '<div class="legend"><p class="eyebrow">where the time went</p>';
    data.activities.forEach(function(a){
      var pct = a.hours/max*100;
      html += '<div class="item"><span class="sw" style="background:'+colorFor(a.name)+'"></span>'+
        '<span class="nm">'+esc(a.name)+'</span>'+
        '<span class="bar"><span style="width:'+pct.toFixed(1)+'%;background:'+colorFor(a.name)+'"></span></span>'+
        '<span class="hr mono">'+a.hours+'h</span></div>';
    });
    html += '</div>';
  }
  document.getElementById('app').innerHTML = html;
}
function esc(s){ return String(s).replace(/[&<>]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]; }); }
__SOURCE__
</script>
</body>
</html>"""

_DECRYPT_BOOTSTRAP = """
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
"""


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
