import re

# Match herdr://focus and standard URLs — covers both hints' built-in plus herdr
_PREFIXES = "file,ftp,ftps,gemini,git,gopher,herdr,http,https,irc,ircs,kitty,mailto,news,sftp,ssh"
_URL_RE = re.compile(r'\b(?:' + '|'.join(re.escape(p) for p in _PREFIXES.split(',')) + r')://\S+')

def mark(text, args, Mark, extra_cli_args, *a):
    for idx, m in enumerate(_URL_RE.finditer(text)):
        s, e = m.span()
        # Strip trailing quote if captured from shell echo ("herdr://...")
        raw = m.group(0)
        if raw.endswith('"') or raw.endswith("'"):
            raw = raw[:-1]
            e -= 1
        yield Mark(idx, s, e, raw, {})

def handle_result(args, data, target_window_id, boss, extra_cli_args, *a):
    for url in data.get('match') or []:
        if url:
            boss.open_url(url)

