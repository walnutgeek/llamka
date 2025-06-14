import sys
from importlib.resources import files  # Python ≥3.9

from streamlit.web import cli as stcli  # Streamlit ≥1.11

# locate app.py inside the installed wheel
app_path = str(files("botglue") / "llit_app/main.py")
streamlit_cmd = ["streamlit", "run", app_path]


def main() -> None:
    # mimic:  streamlit run  /abs/path/to/app.py  [any extra CLI args…]
    sys.argv = streamlit_cmd + sys.argv[1:]
    sys.exit(stcli.main())
