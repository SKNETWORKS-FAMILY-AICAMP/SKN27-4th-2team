import os
from tools.generate_docs import save_docs

def main():
    os.makedirs('./docs', exist_ok=True)

    basic_csv = "./contents/youtube/basic_instruction.csv"
    vet_csv = "./contents/youtube/vet_knowledge.csv"

    save_docs('youtube', basic_csv, './docs/youtube_basic_instruction.json')
    save_docs('youtube', vet_csv, './docs/youtube_vet_knowledge.json')

    for filename in os.listdir("./contents/expert_advice"):
        if filename.endswith(".csv"):
            file_path = os.path.join("./contents/expert_advice", filename)
            save_docs("article", file_path, f"./docs/article_{filename.replace('.csv', '.json')}")

if __name__ == "__main__":
    main()