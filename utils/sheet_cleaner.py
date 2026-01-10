import pandas as pd

def clean_sheet(input_path, output_path):
    if input_path.endswith(".csv"):
        df = pd.read_csv(input_path)
    else:
        df = pd.read_excel(input_path)

    patterns = [
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}",
        r"\+?\d[\d\s\-]{8,}\d"
    ]

    for col in df.columns:
        for p in patterns:
            df[col] = df[col].astype(str).str.replace(p, "", regex=True)

    df.to_excel(output_path, index=False)