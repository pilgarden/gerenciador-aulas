# Gerenciador de Notas e Presenças

Sistema web para gerenciar notas e presenças de alunos por disciplina e semestre, com importação e exportação de planilhas do SIGAA.

## Requisitos

- Python 3.11+

## Desenvolvimento local

```bash
cd gerenciador-aulas
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

set FLASK_APP=run:app
flask db upgrade

python run.py
```

Acesse: http://localhost:5000

No primeiro acesso, crie a conta administrador em `/setup`.

## Deploy na internet

Consulte o guia completo: **[DEPLOY.md](DEPLOY.md)**

Resumo: banco gratuito no **Neon** + app no **Render** (planos free).

## Funcionalidades

- Login multiusuário (admin + professores)
- Semestres, disciplinas e alunos (manual ou importação SIGAA)
- Chamada de presença por aula (Presente / Ausente / Justificado)
- Lançamento de notas com média ponderada
- **Exportação** para planilha `.xls` compatível com reimportação no SIGAA
- **Estatísticas** de frequência e notas por disciplina (gráficos e tabelas)

## Fluxo típico do semestre

1. Importar planilha SIGAA → cria disciplina e alunos
2. Registrar presença a cada aula
3. Lançar notas ao longo do semestre
4. Exportar planilha → reimportar no SIGAA

## Testes

```bash
pytest tests/ -q
```
