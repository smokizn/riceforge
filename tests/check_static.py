#!/usr/bin/env python3
"""Static checks over the repository (no system access, no side effects).

- manifests: well-formed rows, known features/tiers/sources, deploy sources exist
- every command the configs execute maps to a manifest package (or is a shell/coreutils builtin)
- every ~/.config path the configs reference is deployed by the repo or machine-local
- syntax: JSONC, Lua (luac -p), Python, shell (bash -n), TOML
- permissions: scripts are executable
- portability and privacy: no absolute /home/<user> paths, MAC addresses, SSIDs or tokens
"""
import json, os, re, subprocess, sys, tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
fails = []
passes = 0


def ok(name):
    global passes
    passes += 1
    print(f"  ok    {name}")


def bad(name, detail=""):
    fails.append(name)
    print(f"  FAIL  {name}")
    if detail:
        for line in str(detail).splitlines()[:12]:
            print(f"        {line}")


def rows(name):
    for line in (REPO / "manifests" / name).read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            yield line.split("\t")


def tracked_files():
    out = subprocess.run(["git", "-C", str(REPO), "ls-files", "-co", "--exclude-standard"],
                         capture_output=True, text=True)
    if out.returncode != 0:          # not a git checkout (sandbox copy): walk the tree
        return [p for p in REPO.rglob("*") if p.is_file() and ".git" not in p.parts]
    return [REPO / f for f in out.stdout.splitlines() if (REPO / f).exists()]


print("\n── manifests")
features = {r[0]: r[1] for r in rows("features.tsv")}
pkgs, commands = {}, {}
problems = []
for r in rows("packages.tsv"):
    if len(r) != 7:
        problems.append(f"{r[0]}: {len(r)} columns"); continue
    pkg, src, feat, tier, cmds, purpose, alt = r
    if src not in ("repo", "aur"): problems.append(f"{pkg}: source {src}")
    if feat not in features: problems.append(f"{pkg}: unknown feature {feat}")
    if tier not in "12345" or len(tier) != 1: problems.append(f"{pkg}: tier {tier}")
    if pkg in pkgs: problems.append(f"{pkg}: duplicate")
    pkgs[pkg] = r
    for c in ([] if cmds == "-" else cmds.split(",")):
        commands[c] = pkg
ok("packages.tsv well formed") if not problems else bad("packages.tsv well formed", "\n".join(problems))
ok("every feature has packages or is core") if all(
    f in {r[2] for r in pkgs.values()} for f in features) else bad("features without packages",
    [f for f in features if f not in {r[2] for r in pkgs.values()}])
for p in REPO.glob("profiles/*.conf"):
    txt = p.read_text()
    for f in re.findall(r'FEATURES_(?:ADD|REMOVE)="([^"]*)"', txt):
        for x in f.split():
            if x not in features: bad(f"{p.name}: unknown feature {x}")
    for e in re.findall(r'HYPR_EXTRAS="([^"]*)"', txt)[0].split():
        if not (REPO / "config/hypr/extras" / f"{e}.lua").exists(): bad(f"{p.name}: missing extra {e}")
ok("profiles reference known features and extras")

deploy_problems, targets = [], set()
for r in rows("deploy.tsv"):
    if len(r) != 3: deploy_problems.append(f"bad row {r}"); continue
    mode, src, dst = r
    if mode not in ("link", "seed"): deploy_problems.append(f"{dst}: mode {mode}")
    s = src.replace("current/", "themes/nacre/", 1) if src.startswith("current/") else src
    if not (REPO / s).exists() and not (REPO / (s + ".in")).exists():
        deploy_problems.append(f"{dst}: source {src} missing")
    if dst in targets: deploy_problems.append(f"{dst}: duplicate target")
    targets.add(dst)
    if src.startswith("current/"):
        for t in REPO.glob("themes/*/"):
            if not (t / src[8:]).exists() and not (t / (src[8:] + ".in")).exists():
                deploy_problems.append(f"theme {t.name} lacks {src[8:]} (link would dangle)")
ok("deploy.tsv sources exist for every theme") if not deploy_problems else bad("deploy.tsv", "\n".join(deploy_problems))

print("\n── commands the configs run")
# shell words that are not external dependencies
BUILTIN = set("""bash sh python3 env cat echo test [ mkdir date tee printf sleep kill pkill pgrep killall
 command exec true false grep awk sed cut tr head tail wc seq timeout setsid mv cp rm ln readlink basename
 dirname find xargs stat sort uniq id systemctl loginctl sudo pidof f fan done if then fi for do eval cd
 hl.dispatch close activate""".split())
cmd_sources = []
for f in (REPO / "config/hypr").rglob("*.lua"):
    for m in re.finditer(r'exec_cmd\(\s*"((?:[^"\\]|\\.)*)"', f.read_text()):
        cmd_sources.append((f, m.group(1).replace('\\"', '"')))
for f in REPO.glob("themes/*/waybar/config.jsonc"):
    for m in re.finditer(r'"(?:exec|exec-if|on-[a-z-]+|lock|suspend|reload)"\s*:\s*"((?:[^"\\]|\\.)*)"', f.read_text()):
        cmd_sources.append((f, m.group(1).replace('\\"', '"')))
for f in list(REPO.glob("themes/*/session")) + [REPO / "bin/session-lib.sh"]:
    for m in re.finditer(r'(?:start_once\s+\S+|setsid -f)\s+"?([A-Za-z0-9_$/.-]+)', f.read_text()):
        cmd_sources.append((f, m.group(1)))
for f in REPO.glob("themes/*/hyprlock.conf"):
    for m in re.finditer(r'text\s*=\s*cmd\[[^\]]*\]\s*(\S+)', f.read_text()):
        cmd_sources.append((f, m.group(1)))
    for m in re.finditer(r'reload_cmd\s*=\s*(.*)', f.read_text()):
        cmd_sources.append((f, m.group(1)))
for f in [REPO / "config/hypr/hypridle.conf"]:
    for m in re.finditer(r'(?:lock_cmd|before_sleep_cmd|after_sleep_cmd|on-timeout|on-resume)\s*=\s*(.*)', f.read_text()):
        cmd_sources.append((f, m.group(1)))

unknown, missing_paths = set(), set()
for f, cmd in cmd_sources:
    for part in re.split(r"\|\||&&|\||;|\$\(|\)", cmd):
        words = part.strip().split()
        while words and re.match(r"^[A-Z_]+=", words[0]):     # VAR=value prefixes
            words = words[1:]
        if not words: continue
        w = words[0].strip("\"'")
        if w in ("bash", "python3", "sh") and len(words) > 1:
            w = words[1] if not words[1].startswith("-") else (words[2] if len(words) > 2 else "")
        if w.startswith(("~/", "$HOME/", "/")):
            p = w.replace("~/", "").replace("$HOME/", "")
            if w.startswith("/"):
                if not w.startswith(("/usr/", "/sys/", "/tmp/", "/etc/", "/var/")): missing_paths.add((f.name, w))
                continue
            if p.startswith(".config/riceforge/"):
                theme = f.relative_to(REPO).parts[1] if f.relative_to(REPO).parts[0] == "themes" else "nacre"
                rp = p[len(".config/riceforge/"):].replace("current/", f"themes/{theme}/", 1)
                if not (REPO / rp).exists(): missing_paths.add((f.name, w))
            elif p not in targets and not p.startswith(".config/riceforge-local"):
                missing_paths.add((f.name, w))
            continue
        if w.startswith(("$", "-", "{", "'", '"', "%", "!", "[")) or w in BUILTIN or w in commands:
            continue
        if re.match(r"^[a-z0-9][a-z0-9._+-]*$", w):
            unknown.add((f.relative_to(REPO).as_posix(), w))
ok(f"{len(cmd_sources)} command strings: every executable maps to a manifest package") if not unknown \
    else bad("commands not in manifests/packages.tsv", "\n".join(f"{a}: {b}" for a, b in sorted(unknown)))
ok("every script path the configs call is deployed") if not missing_paths \
    else bad("config calls paths the repo does not deploy", "\n".join(f"{a}: {b}" for a, b in sorted(missing_paths)))

print("\n── syntax")
files = tracked_files()
errs = []
for f in files:
    if f.suffix == ".jsonc" or f.suffix == ".json":
        s = f.read_text()
        s = re.sub(r"^\s*//.*$", "", s, flags=re.M); s = re.sub(r",(\s*[}\]])", r"\1", s)
        try: json.loads(s)
        except ValueError as e: errs.append(f"{f.relative_to(REPO)}: {e}")
    elif f.suffix == ".toml":
        try: tomllib.loads(f.read_text())
        except tomllib.TOMLDecodeError as e: errs.append(f"{f.relative_to(REPO)}: {e}")
ok("JSON/JSONC/TOML parse") if not errs else bad("JSON/JSONC/TOML", "\n".join(errs))
lua = [str(f) for f in files if f.suffix == ".lua"]
r = subprocess.run(["luac", "-p", *lua], capture_output=True, text=True) if lua and subprocess.run(
    ["sh", "-c", "command -v luac"], capture_output=True).returncode == 0 else None
if r is None: ok("(luac not installed; Lua syntax skipped — Hyprland verify covers it)")
elif r.returncode == 0: ok(f"Lua syntax ({len(lua)} files)")
else: bad("Lua syntax", r.stderr)
py = [str(f) for f in files if f.suffix == ".py"]
r = subprocess.run([sys.executable, "-I", "-c",
                    "import sys,ast\nfor p in sys.argv[1:]: ast.parse(open(p).read(), p)", *py], capture_output=True, text=True)
ok(f"Python syntax ({len(py)} files)") if r.returncode == 0 else bad("Python syntax", r.stderr)
shells = [f for f in files if f.suffix == ".sh" or f.name in ("setup", "riceforge", "session", "riceforge-shell")
          or (f.is_file() and f.read_bytes()[:40].startswith(b"#!/usr/bin/env bash"))]
serr = [f"{f.relative_to(REPO)}: {r.stderr.strip()}" for f in shells
        if (r := subprocess.run(["bash", "-n", str(f)], capture_output=True, text=True)).returncode]
ok(f"shell syntax ({len(shells)} files)") if not serr else bad("shell syntax", "\n".join(serr))

print("\n── permissions")
need_x = [f for f in files if f.read_bytes()[:2] == b"#!" and f.suffix not in (".in",)
          and "tests" not in f.relative_to(REPO).parts[:1] or f.name == "setup"]
nox = [str(f.relative_to(REPO)) for f in need_x if not os.access(f, os.X_OK)]
ok(f"{len(need_x)} scripts with a shebang are executable") if not nox else bad("scripts not executable", "\n".join(nox))

print("\n── portability and privacy")
user = os.environ.get("USER", "smoke")
pat_home = re.compile(r"/home/[a-z_][a-z0-9_-]*/")
pat_priv = re.compile(r"(?i)\b([0-9a-f]{2}[:][0-9a-f]{2}[:][0-9a-f]{2}[:][0-9a-f]{2}[:][0-9a-f]{2}[:][0-9a-f]{2})\b"
                      r"|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|BEGIN (?:RSA|OPENSSH) PRIVATE KEY"
                      r"|\bpsk\s*=\s*\S+|password\s*=\s*['\"][^'\"]+")
hits, priv = [], []
for f in files:
    if f.suffix in (".png", ".jpg", ".svg", ".mp3", ".otf", ".ttf", ".pyc") or f.name.endswith(".rendered"):
        continue
    rel = f.relative_to(REPO).as_posix()
    if rel == "themes/nacre/walker/layout.xml": continue    # rendered locally, gitignored
    try: txt = f.read_text()
    except UnicodeDecodeError: continue
    for i, line in enumerate(txt.splitlines(), 1):
        if pat_home.search(line) and "tests/check_static.py" not in rel:
            hits.append(f"{rel}:{i}: {line.strip()[:100]}")
        m = pat_priv.search(line)
        if m and "check_static.py" not in rel and not (m.group(1) or "").upper().startswith("02:00:00"):
            priv.append(f"{rel}:{i}: {line.strip()[:100]}")
ok("no absolute /home/<user> paths") if not hits else bad("absolute home paths", "\n".join(hits))
ok("no MAC addresses, keys, tokens or passwords") if not priv else bad("possible private data", "\n".join(priv))
lfs = [f.relative_to(REPO).as_posix() for f in files if f.stat().st_size > 8_000_000]
ok("no file over 8 MB") if not lfs else bad("large files", "\n".join(lfs))

print(f"\n{passes} passed, {len(fails)} failed")
sys.exit(1 if fails else 0)
