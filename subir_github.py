# -*- coding: utf-8 -*-
"""Le token do GitHub do Credential Manager, cria repo privado com nome aleatorio,
ativa GitHub Pages e faz push da pasta Organizacao."""
import ctypes
import ctypes.wintypes as w
import subprocess
import os
import secrets
import string
import time
from pathlib import Path
import urllib.request
import urllib.error
import json

# ---- 1) Ler token do Credential Manager (em memoria, NAO grava em arquivo) ----
advapi = ctypes.windll.advapi32
CRED_TYPE_GENERIC = 1

class CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("Flags", w.DWORD),
        ("Type", w.DWORD),
        ("TargetName", w.LPWSTR),
        ("Comment", w.LPWSTR),
        ("LastWritten", ctypes.c_uint64),
        ("CredentialBlobSize", w.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
        ("Persist", w.DWORD),
        ("AttributeCount", w.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", w.LPWSTR),
        ("UserName", w.LPWSTR),
    ]

advapi.CredReadW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, ctypes.POINTER(ctypes.POINTER(CREDENTIAL))]
advapi.CredReadW.restype = w.BOOL
advapi.CredFree.argtypes = [ctypes.POINTER(CREDENTIAL)]
advapi.CredFree.restype = None

pcred = ctypes.POINTER(CREDENTIAL)()
target = "git:https://github.com"
assert advapi.CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(pcred)), "Token nao encontrado"
cred = pcred.contents
raw = ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize)
TOKEN = raw.decode("utf-16-le").rstrip("\x00").strip()
advapi.CredFree(pcred)
print(f"[OK] Token lido (len={len(TOKEN)})")

# ---- 2) Gerar nome aleatorio pro repo ----
alfabeto = string.ascii_lowercase + string.digits
sufixo = "".join(secrets.choice(alfabeto) for _ in range(8))
REPO = f"agenda-{sufixo}"
USER = "faccod"
print(f"[OK] Nome do repo: {REPO}")

# ---- 3) Criar repo privado via API ----
def api(method, url, data=None):
    req = urllib.request.Request(
        url, method=method,
        data=json.dumps(data).encode() if data else None,
        headers={
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        return e.code, body

print("\n[1/3] Criando repo privado...")
status, resp = api("POST", "https://api.github.com/user/repos", {
    "name": REPO,
    "description": "Agenda pessoal - Matheus (compromissos, tarefas, notas)",
    "private": True,
    "auto_init": False,
    "has_pages": True,
})
if status == 201:
    print(f"  [OK] Repo criado: https://github.com/{USER}/{REPO}")
else:
    print(f"  [ERRO {status}] {resp}")
    if status == 422 and "name" in str(resp):
        print("  Repo com esse nome ja existe, vai dar ruim no push. Tentando usar mesmo assim...")
    else:
        raise SystemExit(1)

# ---- 4) Push dos arquivos via git CLI ----
print("\n[2/3] Fazendo push...")
org_dir = Path(r"C:\Users\Matheus\Documents\Matheus Docs\Organização")

# Acha o git do GitHub Desktop (nao esta no PATH)
GIT_CANDIDATOS = [
    r"C:\Users\Matheus\AppData\Local\GitHubDesktop\app-3.6.2\resources\app\git\mingw64\bin\git.exe",
    r"C:\Program Files\Git\bin\git.exe",
    r"C:\Program Files\Git\cmd\git.exe",
]
GIT = None
for c in GIT_CANDIDATOS:
    if Path(c).exists():
        GIT = c
        break
if not GIT:
    # procura versao mais recente do GitHub Desktop
    base = Path(r"C:\Users\Matheus\AppData\Local\GitHubDesktop")
    if base.exists():
        versoes = sorted(base.glob("app-*"))
        if versoes:
            cand = versoes[-1] / "resources/app/git/mingw64/bin/git.exe"
            if cand.exists():
                GIT = str(cand)
if not GIT:
    print("ERRO: git nao encontrado. Instale Git for Windows ou GitHub Desktop.")
    raise SystemExit(1)
print(f"[OK] git em: {GIT}")
cmds = [
    [GIT, "init", "-b", "main"],
    [GIT, "config", "user.name", "Mavis"],
    [GIT, "config", "user.email", "faccod@gmail.com"],
    [GIT, "remote", "add", "origin", f"https://{TOKEN}@github.com/{USER}/{REPO}.git"],
    [GIT, "add", "."],
    [GIT, "commit", "-m", "feat: agenda inicial (compromissos, tarefas, notas)"],
    [GIT, "push", "-u", "origin", "main", "--force"],
]

for cmd in cmds:
    print(f"  $ {' '.join(cmd[:3])}...")
    r = subprocess.run(cmd, cwd=org_dir, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  [ERRO] {r.stderr.strip()[:300]}")
        if "nothing to commit" in r.stderr:
            continue
        if "already exists" in r.stderr:
            continue
        if r.stdout:
            print(f"  [OUT] {r.stdout.strip()[:300]}")
        # Nao abortar - alguns erros sao benignos
    else:
        if r.stdout:
            print(f"  [OK] {r.stdout.strip()[:150]}")

# ---- 5) Ativar GitHub Pages (apontando pra branch main / root) ----
print("\n[3/3] Ativando GitHub Pages...")
status, resp = api("POST", f"https://api.github.com/repos/{USER}/{REPO}/pages", {
    "source": {"branch": "main", "path": "/"},
})
if status in (201, 204):
    print("  [OK] GitHub Pages ativado!")
elif status == 409:
    print("  [INFO] Pages ja estava ativado")
else:
    print(f"  [WARN] Status {status}: {resp}")

pages_url = f"https://{USER}.github.io/{REPO}/"
ics_url = f"{pages_url}compromissos.ics"
print()
print("=" * 60)
print("URL publica do .ics:")
print(f"  {ics_url}")
print()
print("URL da pagina (pra ver arquivos):")
print(f"  {pages_url}")
print("=" * 60)
print()
print("COPIE a URL do .ics e assine no celular:")
print("  iPhone: Configuracoes > Calendario > Contas > Adicionar > Outra > Calendario Assinado > cola a URL")
print("  Android (Google Calendar): PC > calendar.google.com > Configuracoes > Adicionar calendario > Da URL")
print()
print(f"Nome aleatorio do repo: {REPO} (faca bookmark!)")
