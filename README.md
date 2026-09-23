Учебный проект "REST API для оценки риска сельскохозяйственных предприятий"

## Запуск 
uv
```bash
uv sink
uv run uvicorn main:app --reload
```

no uv
```bash
python -m venv .venv
source ./venv/bin/activate (win: ./venv/Scripts/activate)
pip install .
uvicorn main:app --reload
```
