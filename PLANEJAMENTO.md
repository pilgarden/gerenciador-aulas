# Gerenciador de Notas e Presenças — Plano do Projeto

## Objetivo

Sistema web para gerenciar **notas**, **presenças** e **disciplinas** ao longo do semestre, com login seguro, persistência de dados e importação da planilha exportada pelo SIGAA.

---

## Análise da Planilha SIGAA

Arquivo analisado: `notas_DEC10058_T01_20262.xls.xls`

| Linha | Conteúdo |
|-------|----------|
| 1 | Título: "PLANILHA DE NOTAS" |
| 2 | Disciplina: `DEC10058 - INTRODUÇÃO AO MÉTODO DOS ELEMENTOS FINITOS (60h) - Turma: 01 (2026.2)` |
| 4–9 | Instruções de preenchimento |
| 11 | Cabeçalho dos alunos |
| 12+ | Dados dos alunos |

**Colunas dos alunos (a partir da linha 11):**

| Coluna | Campo SIGAA | Uso no sistema |
|--------|-------------|----------------|
| Matrícula | Identificador único | Chave do aluno na disciplina |
| Nome | Nome completo | Exibição |
| Unid. 1, Unid. 2, … | Notas por unidade | Avaliações (configurável por disciplina) |
| Rec. | Recuperação | Nota de recuperação |
| Resultado | Média/resultado | Calculado ou importado |
| Faltas | Total de faltas | Presença (contador SIGAA) |
| Sit. | Situação | Aprovado/reprovado/etc. |

**Parser de importação:** ignorar linhas 1–10; ler cabeçalho na linha 11; extrair código/turma/semestre da linha 2 via regex; importar alunos a partir da linha 12.

---

## Requisitos (Versão 1)

### Funcionalidades

- [ ] Login com usuário e senha (múltiplos usuários; cadastro inicial do administrador)
- [ ] CRUD de **semestres** (ex.: 2026.2)
- [ ] CRUD de **disciplinas** (código, nome, turma, carga horária, semestre)
- [ ] CRUD de **alunos** (manual ou importação SIGAA)
- [ ] **Importação** de planilha `.xls` do SIGAA (cria/atualiza disciplina + alunos)
- [ ] Registro de **presença por aula** (data, presente/ausente/justificado)
- [ ] Registro de **notas** por avaliação/unidade
- [ ] **Dashboard** com resumo: faltas, médias, situação
- [ ] **Exportação** para planilha (compatível com reimportação no SIGAA)

### Fora do escopo (v1)

- Controle de presença automático (digital/biometria) — reservar arquitetura para v2
- Permissões granulares por disciplina (todos os usuários têm acesso igual na v1)
- App mobile nativo

---

## Stack Tecnológica Recomendada

| Camada | Tecnologia | Motivo |
|--------|------------|--------|
| Backend | **Python + Flask** | Você já usa Python; simples de manter |
| Banco de dados | **SQLite** (local) / **PostgreSQL** (nuvem) | Gratuito, persistente |
| ORM | **SQLAlchemy + Flask-Migrate** | Migrações e modelos claros |
| Autenticação | **Flask-Login + bcrypt** | Login seguro, sem custo |
| Frontend | **HTML + Bootstrap 5 + Jinja2** | Leve, funciona em qualquer navegador |
| Planilhas | **pandas + xlrd + openpyxl** | Leitura/escrita `.xls` e `.xlsx` |
| Deploy | **Render.com** (app) + **Neon** (banco) | Gratuito e persistente o semestre inteiro |

### Decisões confirmadas

- **Framework:** Flask
- **Hospedagem:** nuvem (PC não precisa ficar ligado)
- **Usuários:** múltiplos; o primeiro cadastro é o **administrador** (você), que pode convidar/criar outros professores

---

## Modelo de Dados

```
Usuario
  id, email, senha_hash, nome, papel (admin | professor), ativo, criado_em

Semestre
  id, codigo (2026.2), ativo

Disciplina
  id, semestre_id, codigo (DEC10058), nome, turma (01),
  carga_horaria, aulas_previstas

AlunoDisciplina  (matrícula na turma)
  id, disciplina_id, matricula, nome, faltas_sigaa, situacao

Aula
  id, disciplina_id, data, numero, conteudo (opcional)

Presenca
  id, aula_id, aluno_disciplina_id, status (P/A/J)

Avaliacao
  id, disciplina_id, nome (Unid. 1), peso, ordem

Nota
  id, avaliacao_id, aluno_disciplina_id, valor
```

---

## Telas Principais

1. **Login** — email/senha
2. **Início** — semestre ativo, disciplinas, atalhos
3. **Disciplinas** — listar, criar, editar, excluir
4. **Alunos** — lista por disciplina, cadastro manual, importar SIGAA
5. **Chamada** — grade data × aluno (checkboxes)
6. **Notas** — tabela editável estilo planilha
7. **Relatórios** — faltas, médias, exportar XLS
8. **Usuários** (admin) — criar/desativar contas de professores

---

## Autenticação e Usuários

| Papel | Permissões (v1) |
|-------|-----------------|
| **admin** | Tudo + gerenciar usuários (criar, desativar, redefinir senha) |
| **professor** | Semestres, disciplinas, alunos, presença, notas, importação, exportação |

**Fluxo inicial:**

1. No primeiro deploy, o banco está vazio → tela de **Setup** pede nome, e-mail e senha do administrador.
2. Esse cadastro cria o usuário com `papel = admin`.
3. Depois disso, a tela de setup fica desabilitada; novos usuários só via painel admin.
4. Admin convida colegas: informa e-mail + senha temporária (ou link de convite na v2).

**Segurança básica:**

- Senhas com bcrypt (via Werkzeug)
- Sessão com cookie HTTP-only
- `SECRET_KEY` via variável de ambiente no Render

---

## Importação SIGAA — Fluxo

```
Upload .xls
    → Detectar linha da disciplina (linha 2)
    → Extrair: código, nome, turma, semestre, CH
    → Detectar cabeçalho (linha com "Matrícula")
    → Para cada aluno:
        - Se matrícula existe na disciplina → atualizar
        - Senão → criar AlunoDisciplina
    → Opcional: importar notas/faltas já preenchidas
    → Exibir preview antes de confirmar
```

---

## Hospedagem Gratuita na Internet

Como o PC não ficará sempre ligado, a aplicação deve rodar na nuvem. Abaixo, as limitações reais dos planos free (2026).

### Comparativo dos planos gratuitos

| Plataforma | O que oferece de graça | Limitações importantes | Serve para o semestre? |
|------------|------------------------|------------------------|------------------------|
| **Render** (app web) | Web service Flask, HTTPS, deploy via Git | Dorme após **15 min** sem acesso; demora **~1 min** para acordar; **750 h/mês** de instância free | ✅ Sim (com ressalva do "cold start") |
| **Render** (Postgres) | 1 GB de armazenamento | **Expira em 30 dias**; sem backup; 1 banco por conta | ❌ Não — curto demais para um semestre |
| **Neon** (Postgres) | 0,5 GB/projeto, 100 h compute/mês | Escala para zero após 5 min idle; 5 GB egress/mês | ✅ **Sim — melhor banco gratuito** |
| **PythonAnywhere** | 1 web app Flask, SQLite no disco | **100 s de CPU/mês**; app expira em **1 mês** (renovar clicando); internet externa restrita; sem MySQL (contas novas) | ⚠️ Possível, mas apertado |
| **Supabase** | 500 MB × 2 projetos, Postgres + auth | Pausa após **7 dias** sem uso | ⚠️ OK se acessar toda semana |
| **Railway** | $5 de crédito único (trial) | Depois: **$5/mês** mínimo (Hobby) | ❌ Não é free permanente |
| **Fly.io** | 3 VMs compartilhadas (256 MB) | IPv4 custa ~**$3,60/mês**; Postgres não é gerenciado | ❌ Não totalmente free |

### Recomendação: Render + Neon

```
[Seu navegador] → [Render — Flask app] → [Neon — PostgreSQL]
     HTTPS              free tier              free permanente
```

**Por quê essa combinação?**

1. **Neon** não expira — seus dados sobrevivem o semestre inteiro (0,5 GB é mais que suficiente para dezenas de turmas).
2. **Render** faz deploy simples de Flask a partir do GitHub, com HTTPS incluso.
3. Ambos são gratuitos, sem cartão de crédito.

**O que você vai sentir na prática:**

- Se ninguém acessar por 15 min, a **primeira visita** demora ~1 minuto (o serviço "acorda"). Depois disso, fica rápido.
- Solução opcional: um serviço de "ping" gratuito (ex.: UptimeRobot) acessando a URL a cada 14 min — mantém o app acordado dentro das 750 h/mês.

### PythonAnywhere — por que não é ideal

Funciona para Flask com SQLite persistente, mas o plano free de 2026 ficou muito restritivo: 100 segundos de CPU por mês e renovação manual do web app a cada mês. Para uso frequente durante o semestre (chamada, notas, importação), Render + Neon é mais confiável.

### Fluxo de deploy (quando implementarmos)

1. Desenvolver localmente com SQLite
2. Criar banco free no [Neon](https://neon.tech)
3. Conectar repositório GitHub ao [Render](https://render.com)
4. Configurar variável `DATABASE_URL` apontando para o Neon
5. Primeiro acesso: criar conta admin (você) via tela de setup inicial

---

## Arquitetura para Presença Automática (v2)

Reservar desde já:

- Tabela `DispositivoPresenca` (id, nome, tipo: digital/rfid/qrcode)
- Endpoint `POST /api/presenca/registrar` com token do dispositivo
- Campo `origem` em `Presenca`: manual | automatico | importado

Isso permite adicionar leitor de digital depois sem refatorar o núcleo.

---

## Estrutura de Pastas

```
gerenciador-aulas/
├── app/
│   ├── __init__.py          # Factory Flask
│   ├── models.py            # SQLAlchemy models
│   ├── auth/                # Login, registro
│   ├── disciplinas/         # CRUD disciplinas
│   ├── alunos/              # CRUD + importação
│   ├── presencas/           # Chamada
│   ├── notas/               # Avaliações e notas
│   ├── services/
│   │   └── sigaa_import.py  # Parser da planilha
│   ├── templates/           # HTML Jinja2
│   └── static/              # CSS, JS
├── migrations/              # Flask-Migrate
├── instance/                # SQLite local (gitignore)
├── tests/
├── config.py
├── requirements.txt
├── run.py
├── PLANEJAMENTO.md
└── README.md
```

---

## Cronograma Sugerido

| Fase | Entregas | Estimativa |
|------|----------|------------|
| 1 | Modelos, login, layout base | 2–3 dias |
| 2 | Disciplinas + alunos manuais | 2 dias |
| 3 | Importação SIGAA | 2 dias |
| 4 | Chamada de presença | 2 dias |
| 5 | Notas e relatórios | 2–3 dias |
| 6 | Exportação XLS + deploy | 2 dias |

**Total v1:** ~2–3 semanas (trabalho parcial)

---

## Próximos Passos

1. ~~Confirmar stack (Flask) e hospedagem~~ ✅ Flask + Render + Neon
2. Implementar Fase 1 (login, setup admin, modelos, layout)
3. Testar importação com a planilha real do DEC10058
4. Deploy no Render + Neon
5. Usar na disciplina atual e iterar
