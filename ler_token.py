# -*- coding: utf-8 -*-
"""Le o token do GitHub salvo no Windows Credential Manager via Win32 API."""
import ctypes
import ctypes.wintypes as w
from pathlib import Path

advapi = ctypes.windll.advapi32
credui = ctypes.windll.credui

CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2

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

targets = [
    "git:https://github.com",
    "LegacyGeneric:target=git:https://github.com",
    "GitHub - https://api.github.com/faccod",
]

found = []
for target in targets:
    pcred = ctypes.POINTER(CREDENTIAL)()
    if advapi.CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(pcred)):
        cred = pcred.contents
        size = cred.CredentialBlobSize
        # IMPORTANTE: usar Unicode (UTF-16LE) pq Credential Manager armazena assim
        raw = ctypes.string_at(cred.CredentialBlob, size)
        token = raw.decode("utf-16-le").rstrip("\x00").strip()
        found.append((target, cred.UserName, token))
        advapi.CredFree(pcred)

if found:
    for t, u, tok in found:
        print(f"Target: {t}")
        print(f"  User: {u}")
        print(f"  Token (len={len(tok)}): {tok[:4]}{'*' * (len(tok)-8)}{tok[-4:]}")
        print()
else:
    print("Nenhum token encontrado.")
