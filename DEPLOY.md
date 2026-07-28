# Deploy — Render + Neon

Guia passo a passo para colocar o **Gerenciador de Aulas** na internet gratuitamente.

## Pré-requisitos

- Conta no [GitHub](https://github.com)
- Conta no [Neon](https://neon.tech) (banco PostgreSQL gratuito)
- Conta no [Render](https://render.com) (hospedagem gratuita)

---

## 1. Banco de dados (Neon)

1. Acesse [neon.tech](https://neon.tech) e crie um projeto
2. Anote a **Connection string** (formato `postgresql://usuario:senha@host/db?sslmode=require`)
3. O plano free **não expira** — ideal para uso durante o semestre

---

## 2. Repositório GitHub

```bash
cd gerenciador-aulas
git init
git add .
git commit -m "Gerenciador de aulas — versão inicial"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/gerenciador-aulas.git
git push -u origin main
```

---

## 3. Web Service (Render)

### Opção A — Blueprint (automático)

1. No Render: **New → Blueprint**
2. Conecte o repositório GitHub
3. O arquivo `render.yaml` configura o serviço automaticamente
4. Quando solicitado, informe a variável `DATABASE_URL` com a connection string do Neon

### Opção B — Manual

1. **New → Web Service** → conecte o repositório
2. Configurações:
   - **Runtime:** Python 3
   - **Build Command:** `./build.sh`
   - **Start Command:** `gunicorn run:app --bind 0.0.0.0:$PORT`
3. Variáveis de ambiente:

| Variável | Valor |
|----------|-------|
| `FLASK_APP` | `run:app` |
| `FLASK_CONFIG` | `production` |
| `SECRET_KEY` | string aleatória longa (ex.: output de `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `DATABASE_URL` | connection string do Neon |

4. Clique em **Create Web Service**

---

## 4. Primeiro acesso

1. Aguarde o deploy (build roda `flask db upgrade` automaticamente)
2. Acesse a URL gerada pelo Render (ex.: `https://gerenciador-aulas.onrender.com`)
3. Na primeira visita, crie a conta **administrador** em `/setup`
4. Pronto — use normalmente de qualquer computador

---

## Limitações do plano free (Render)

| Item | Comportamento |
|------|---------------|
| Cold start | Após 15 min sem acesso, a 1ª visita demora ~1 min |
| Horas/mês | 750 h de instância (suficiente para uso pessoal) |
| HTTPS | Incluso automaticamente |

**Dica:** use [UptimeRobot](https://uptimerobot.com) (grátis) para pingar a URL a cada 14 min e evitar cold starts frequentes.

---

## Atualizações

A cada `git push` na branch principal, o Render redeploya automaticamente e executa as migrações do banco.

```bash
git add .
git commit -m "Descrição da alteração"
git push
```

---

## Solução de problemas

**Erro de conexão com banco:** verifique se `DATABASE_URL` está correta e se o Neon está ativo.

**Build falha em `flask db upgrade`:** confira se `FLASK_APP=run:app` está definida.

**502 Bad Gateway:** o serviço pode estar acordando — aguarde ~1 min e recarregue.

**Sessão expira / CSRF:** em produção, acesse sempre via HTTPS (URL do Render).
