"""Testes básicos da Fase 1."""
import re
import sys

import requests

BASE = "http://127.0.0.1:5000"


def get_csrf(html):
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not match:
        raise RuntimeError("CSRF token não encontrado")
    return match.group(1)


def main():
    s = requests.Session()

    r = s.get(f"{BASE}/setup", timeout=5)
    r.raise_for_status()
    assert "Configura" in r.text
    print("OK: /setup")

    csrf = get_csrf(r.text)
    r = s.post(
        f"{BASE}/setup",
        data={
            "csrf_token": csrf,
            "nome": "Pedro Admin",
            "email": "pedro@teste.com",
            "senha": "senha1234",
            "confirmar_senha": "senha1234",
            "submit": "Criar conta administrador",
        },
        allow_redirects=False,
        timeout=5,
    )
    assert r.status_code in (302, 303)
    print("OK: admin criado")

    r = s.get(f"{BASE}/login", timeout=5)
    csrf = get_csrf(r.text)
    r = s.post(
        f"{BASE}/login",
        data={
            "csrf_token": csrf,
            "email": "pedro@teste.com",
            "senha": "senha1234",
            "submit": "Entrar",
        },
        allow_redirects=False,
        timeout=5,
    )
    assert r.status_code in (302, 303)
    print("OK: login")

    r = s.get(f"{BASE}/", timeout=5)
    assert "Painel" in r.text
    print("OK: dashboard")

    r = s.get(f"{BASE}/usuarios/", timeout=5)
    assert "Usu" in r.text
    print("OK: usuarios")
    print("Todos os testes passaram.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FALHA: {exc}")
        sys.exit(1)
