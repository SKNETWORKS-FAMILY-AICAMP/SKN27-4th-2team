# AKC Breed Info Preprocessing

This folder stores preprocessing outputs derived from `../akc_breed_info.csv`.

Step 1 is source preservation:

- The original source file remains unchanged at `database/akc/akc_breed_info.csv`.
- `akc_breed_info_step1_original_copy.csv` is a working copy for later preprocessing steps.
- Later steps should create new files in this folder instead of modifying the original CSV.

Planned final output:

- Search-ready JSON documents for vector database ingestion.
