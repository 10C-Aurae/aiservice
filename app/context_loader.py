import os

def load_context():
    context = ""
    base_path = "context"

    for file in os.listdir(base_path):
        with open(os.path.join(base_path, file), "r", encoding="utf-8") as f:
            context += f"\n--- {file} ---\n"
            context += f.read()

    return context
