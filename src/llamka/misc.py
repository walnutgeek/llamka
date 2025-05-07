from pathlib import Path


def delete_file_ensure_parent_dir(test_db_path: Path | str) -> Path:
    """make sure that db does not exist, but parent dir does"""
    test_db_path = Path(test_db_path)
    if test_db_path.exists():
        test_db_path.unlink()
    if not test_db_path.parent.is_dir():
        test_db_path.parent.mkdir(parents=True, exist_ok=True)
    return test_db_path
