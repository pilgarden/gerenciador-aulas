# Deploy — Render + Neon

Guia passo a passo para colocar o **Gerenciador de Aulas** na internet gratuitamente.

## Pré-requisitos

- Conta no [GitHub](https://github.com)
- Conta no [Neon](https://neon.tech) (banco PostgreSQL gratuito)
- Conta no [Render](https://render.com) (hospedagem gratuita)
- Git instalado ([git-scm.com](https://git-scm.com/download/win)) — feche e reabra o terminal após instalar

---

## Passo 1 — Banco de dados (Neon)

1. Acesse [neon.tech](https://neon.tech) → **Sign up** (grátis)
2. **New Project** → escolha região próxima (ex.: US East)
3. No painel, copie a **Connection string** (botão **Connect**)
   - Formato: `postgresql://usuario:senha@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`
4. Guarde em local seguro — será usada no Render

> O plano free do Neon **não expira** e comporta o uso de um semestre inteiro.

---

## Passo 2 — Enviar código para o GitHub

Abra um **novo** PowerShell na pasta do projeto:

```powershell
cd C:\Users\Pedro\Desktop\gerenciador-aulas

# Se ainda não commitou:
git add .
git commit -m "Gerenciador de aulas - versao inicial"
git branch -M main
```

No GitHub (site):

1. **New repository** → nome: `gerenciador-aulas` → **Create** (sem README)
2. Copie os comandos que o GitHub mostra, ou:

```powershell
git remote add origin https://github.com/SEU_USUARIO/gerenciador-aulas.git
git push -u origin main
```

**Alternativa sem terminal:** instale [GitHub Desktop](https://desktop.github.com), adicione a pasta e publique.

---

## Passo 3 — Web Service (Render)

### Opção A — Blueprint (recomendada)

1. [render.com](https://render.com) → **Sign up** → conecte o GitHub
2. **New +** → **Blueprint**
3. Selecione o repositório `gerenciador-aulas`
4. O Render detecta o `render.yaml` automaticamente
5. Quando pedir `DATABASE_URL`, cole a connection string do **Neon**
6. **Apply** → aguarde o deploy (~3–5 min)

### Opção B — Manual

1. **New +** → **Web Service** → conecte o repositório
2. Configurações:

| Campo | Valor |
|-------|-------|
| Build Command | `./build.sh` |
| Start Command | `gunicorn run:app --bind 0.0.0.0:$PORT` |

3. Variáveis de ambiente (**Environment**):

| Variável | Valor |
|----------|-------|
| `FLASK_APP` | `run:app` |
| `FLASK_CONFIG` | `production` |
| `SECRET_KEY` | string aleatória longa (veja abaixo) |
| `DATABASE_URL` | connection string do Neon |

4. **Create Web Service**

**Gerar SECRET_KEY** (PowerShell):

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Passo 4 — Primeiro acesso

1. Aguarde o deploy terminar (status **Live**)
2. Acesse a URL gerada, ex.: `https://gerenciador-aulas.onrender.com`
3. Na **primeira visita**, crie sua conta **administrador** em `/setup`
4. Pronto — acesse de qualquer computador ou celular

> A primeira visita após 15 min sem uso pode demorar ~1 min (serviço acordando).

---

## Passo 5 — Importar sua turma

1. Login → **Disciplinas** → **Importar SIGAA**
2. Envie a planilha `.xls` exportada do SIGAA
3. Confirme → semestre, disciplina e alunos criados automaticamente

---

## Limitações do plano free (Render)

| Item | Comportamento |
|------|---------------|
| Cold start | Após 15 min sem acesso, 1ª visita demora ~1 min |
| Horas/mês | 750 h (suficiente para uso pessoal) |
| HTTPS | Incluso automaticamente |

**Dica:** [UptimeRobot](https://uptimerobot.com) (grátis) pode pingar a URL a cada 14 min para reduzir cold starts.

---

## Atualizações futuras

```powershell
git add .
git commit -m "Descricao da alteracao"
git push
```

O Render redeploya automaticamente e executa `flask db upgrade`.

---

## Solução de problemas

| Problema | Solução |
|----------|---------|
| Build falha em `flask db upgrade` | Verifique se `DATABASE_URL` e `FLASK_APP` estão definidas **antes** do deploy |
| Erro de conexão com banco | Confira a connection string do Neon; use `postgresql://` (não `postgres://`) |
| 502 Bad Gateway | Serviço acordando — aguarde ~1 min e recarregue |
| CSRF / sessão | Acesse sempre via HTTPS (URL do Render) |
| `git` não reconhecido | Reinstale Git e **reabra o terminal** |
