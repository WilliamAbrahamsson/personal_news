try:
    # When running from the project root: `python backend/app.py` or `python -m backend.app`
    from backend import create_app
except ModuleNotFoundError:
    # When running inside the backend folder: `python app.py`
    import os, sys
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from backend import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
