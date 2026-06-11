# AKC Saved HTML Parser

This parser converts locally saved AKC breed pages into a CSV.

## Folder Layout

- Put saved breed pages here: `database/akc/html_pages/`
- Output CSV defaults to: `database/akc/akc_breeds_from_html.csv`

Example:

```text
database/akc/html_pages/
  affenpinscher.html
  bichon-frise.html
  golden-retriever.html
```

## Run

From the project root:

```bash
python database/akc/parse_saved_breed_html.py
```

Custom paths:

```bash
python database/akc/parse_saved_breed_html.py --input-dir database/akc/html_pages --output database/akc/akc_breeds_from_html.csv
```

## Output Columns

The CSV has one row per breed and includes:

- `breed_name`, `breed_url`
- `height`, `weight`, `life_expectancy`
- all requested AKC trait columns
- `colors`, `markings`
- `about_the_breed`
- `health`, `grooming`, `exercise`, `training`, `nutrition`
- `history`

Trait score fields are stored as `filled/total`, for example `3/5`.
Choice fields such as `Coat Type` and `Coat Length` are stored as selected values joined with ` | `.

## Notes

- The parser does not make network requests.
- It only reads saved `.html` and `.htm` files.
- If a section is missing from a saved page, the matching CSV field is left blank.
