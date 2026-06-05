import csv
import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SOURCE = BASE_DIR / "dogapi_akc_matched_breeds.csv"
TARGET = BASE_DIR / "dogapi_akc_matched_breeds_ko.csv"

BREED_GROUP_MAP = {
    "Toy": "토이",
    "Hound": "하운드",
    "Terrier": "테리어",
    "Working": "워킹",
    "Sporting": "스포팅",
    "Herding": "목양견",
    "Non-Sporting": "논스포팅",
    "Foundation Stock Service": "파운데이션 스톡 서비스",
    "Spitz and Primitive Types": "스피츠 및 원시형",
}

TEMPERAMENT_MAP = {
    "adaptable": "적응력이 좋은",
    "affectionate": "애정이 많은",
    "agile": "민첩한",
    "alert": "경계심이 있는",
    "aloof": "도도한",
    "amiable": "상냥한",
    "athletic": "운동 능력이 좋은",
    "calm": "차분한",
    "charming": "매력적인",
    "confident": "자신감 있는",
    "courageous": "용감한",
    "curious": "호기심 많은",
    "determined": "의지가 강한",
    "devoted": "헌신적인",
    "dignified": "품위 있는",
    "docile": "온순한",
    "eager to please": "사람을 기쁘게 하려는",
    "easygoing": "느긋한",
    "energetic": "활동적인",
    "even-tempered": "성격이 안정적인",
    "fearless": "두려움이 적은",
    "friendly": "친근한",
    "gentle": "부드러운",
    "good-natured": "성품이 좋은",
    "happy": "밝은",
    "hardy": "강인한",
    "independent": "독립적인",
    "intelligent": "영리한",
    "lively": "활기찬",
    "loyal": "충성심 강한",
    "merry": "명랑한",
    "mischievous": "장난기 있는",
    "optimistic": "낙천적인",
    "outgoing": "외향적인",
    "patient": "참을성 있는",
    "playful": "장난기 많은",
    "protective": "보호 본능이 강한",
    "reserved": "신중한",
    "sensitive": "섬세한",
    "smart": "똑똑한",
    "spirited": "활발한",
    "work-focused": "일에 집중하는",
}

COAT_TYPE_MAP = {
    "Corded": "끈 모양 털",
    "Curly": "곱슬털",
    "Double": "이중모",
    "Hairless": "무모",
    "Rough": "거친 털",
    "Silky": "비단결 털",
    "Smooth": "매끄러운 털",
    "Wavy": "물결 털",
    "Wiry": "뻣뻣한 털",
}

COAT_LENGTH_MAP = {
    "Short": "짧은 털",
    "Medium": "중간 길이 털",
    "Long": "긴 털",
}

COLOR_WORD_MAP = {
    "Agouti": "아구티",
    "Apricot": "살구색",
    "Beige": "베이지",
    "Belge": "벨지",
    "Biscuit": "비스킷색",
    "Black": "검정",
    "Blenheim": "블렌하임",
    "Blonde": "블론드",
    "Blue": "블루",
    "Blk": "검정",
    "Bronze": "청동색",
    "Brindle": "브린들",
    "Brindled": "브린들",
    "Brown": "갈색",
    "Buff": "버프색",
    "Cafe Au Lait": "카페오레색",
    "Charcoal": "차콜",
    "Chestnut": "밤색",
    "Chocolate": "초콜릿색",
    "Cinnamon": "시나몬색",
    "Copper": "구리색",
    "Cream": "크림색",
    "Dark Brown": "진갈색",
    "Fawn": "황갈색",
    "Gold": "금색",
    "Golden": "골든",
    "Gray": "회색",
    "Graybrown": "회갈색",
    "Grizzle": "그리즐",
    "Harlequin": "할리퀸",
    "Isabella": "이사벨라",
    "Lemon": "레몬색",
    "Lilac": "라일락색",
    "Liver": "리버색",
    "Mahogany": "마호가니색",
    "Mantle": "맨틀",
    "Merle": "멀",
    "Mkngs": "무늬",
    "Orange": "오렌지색",
    "On": "바탕",
    "Overlay": "오버레이",
    "Palomino": "팔로미노",
    "Pepper": "페퍼",
    "Pink": "분홍색",
    "Platinum": "플래티넘",
    "Red": "붉은색",
    "Roan": "로언",
    "Rose": "로즈",
    "Ruby": "루비색",
    "Rust": "녹슨 갈색",
    "Sable": "세이블",
    "Sabled": "세이블",
    "Salt": "솔트",
    "Sandy": "모래색",
    "Seal": "씰색",
    "Sesame": "참깨색",
    "Silver": "은색",
    "Slate": "슬레이트색",
    "Shading": "셰이딩",
    "Tan": "탄색",
    "Tawny": "황갈색",
    "Trim": "트림",
    "Undercoat": "언더코트",
    "Wheaten": "밀색",
    "White": "흰색",
    "Wild Boar": "와일드보어",
    "Wolf": "늑대색",
    "Wolfgray": "늑대회색",
    "Yellow": "노란색",
}

MARKING_WORD_MAP = {
    **COLOR_WORD_MAP,
    "Badger": "배저 무늬",
    "Belton": "벨턴 무늬",
    "Bicolor": "바이컬러",
    "Bishop": "비숍 무늬",
    "Blanket": "블랭킷 무늬",
    "Blaze": "블레이즈 무늬",
    "Brindle": "브린들",
    "Brindled": "브린들",
    "Brindling": "브린들",
    "Cap": "캡 무늬",
    "Domino": "도미노 무늬",
    "Grizzle": "그리즐",
    "Mask": "마스크",
    "Masked": "마스크",
    "Markings": "무늬",
    "Overlay": "오버레이",
    "Patches": "패치",
    "Piebald": "파이볼드",
    "Pinto": "핀토",
    "Points": "포인트",
    "Roan": "로언",
    "Saddle": "새들 무늬",
    "Saddleback": "새들백",
    "Sabling": "세이블",
    "Shading": "셰이딩",
    "Spotted": "점무늬",
    "Ticked": "틱 무늬",
    "Tri": "트라이",
}

ORIGIN_EXACT_MAP = {
    "Afghanistan": "아프가니스탄",
    "Central Africa": "중앙아프리카",
    "Central Asia": "중앙아시아",
    "Caucasus Mountains": "캅카스 산맥",
    "England": "영국",
    "France": "프랑스",
    "Germany": "독일",
    "Japan": "일본",
    "United Kingdom": "영국",
    "United States": "미국",
}

ORIGIN_COUNTRY_MAP = {
    "Afghanistan": "아프가니스탄",
    "Argentina": "아르헨티나",
    "Australia": "호주",
    "Belgium": "벨기에",
    "Brazil": "브라질",
    "Burkina Faso": "부르키나파소",
    "Canada": "캐나다",
    "China": "중국",
    "Croatia": "크로아티아",
    "Cuba": "쿠바",
    "Denmark": "덴마크",
    "England": "영국",
    "Finland": "핀란드",
    "France": "프랑스",
    "Germany": "독일",
    "Greece": "그리스",
    "Hungary": "헝가리",
    "Iceland": "아이슬란드",
    "Ireland": "아일랜드",
    "Italy": "이탈리아",
    "Japan": "일본",
    "Korea": "한국",
    "Mali": "말리",
    "Malta": "몰타",
    "Mexico": "멕시코",
    "Mali": "말리",
    "Malta": "몰타",
    "Netherlands": "네덜란드",
    "Niger": "니제르",
    "Norway": "노르웨이",
    "Peru": "페루",
    "Poland": "폴란드",
    "Portugal": "포르투갈",
    "Russia": "러시아",
    "Scotland": "영국",
    "Serbia": "세르비아",
    "South Africa": "남아프리카공화국",
    "Spain": "스페인",
    "Sweden": "스웨덴",
    "Switzerland": "스위스",
    "Thailand": "태국",
    "Turkey": "튀르키예",
    "United Kingdom": "영국",
    "United States": "미국",
    "Wales": "영국",
}

BREED_ORIGIN_COUNTRY_MAP = {
    "Basenji": "콩고민주공화국",
    "Boerboel": "남아프리카공화국",
    "Border Collie": "영국",
    "Caucasian Shepherd Dog": "러시아",
    "Dandie Dinmont Terrier": "영국",
    "Rhodesian Ridgeback": "짐바브웨",
    "Sloughi": "모로코",
}

ORIGIN_TOKEN_MAP = {
    "Afghanistan": "아프가니스탄",
    "Africa": "아프리카",
    "Alaska": "알래스카",
    "America": "미국",
    "Argentina": "아르헨티나",
    "Asia": "아시아",
    "Australia": "호주",
    "Belgium": "벨기에",
    "Brazil": "브라질",
    "Burkina Faso": "부르키나파소",
    "Canada": "캐나다",
    "Central": "중앙",
    "China": "중국",
    "Croatia": "크로아티아",
    "Cuba": "쿠바",
    "Denmark": "덴마크",
    "England": "영국",
    "Finland": "핀란드",
    "France": "프랑스",
    "Germany": "독일",
    "Greece": "그리스",
    "Hungary": "헝가리",
    "Iceland": "아이슬란드",
    "Ireland": "아일랜드",
    "Italy": "이탈리아",
    "Japan": "일본",
    "Korea": "한국",
    "Mexico": "멕시코",
    "Mali": "말리",
    "Malta": "몰타",
    "Netherlands": "네덜란드",
    "Niger": "니제르",
    "Norway": "노르웨이",
    "Peru": "페루",
    "Poland": "폴란드",
    "Portugal": "포르투갈",
    "Russia": "러시아",
    "Scotland": "스코틀랜드",
    "Serbia": "세르비아",
    "Spain": "스페인",
    "Sweden": "스웨덴",
    "Switzerland": "스위스",
    "Thailand": "태국",
    "Turkey": "튀르키예",
    "United Kingdom": "영국",
    "United States": "미국",
    "Wasilla": "와실라",
    "Wales": "웨일스",
    "Yorkshire": "요크셔",
}


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_array(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item)]
    except json.JSONDecodeError:
        return []
    return []


def join_unique(values):
    output = []
    seen = set()
    for value in values:
        value = value.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return ", ".join(output)


def translate_temperament(value):
    parts = [part.strip() for part in value.split(",") if part.strip()]
    return join_unique(TEMPERAMENT_MAP.get(part.lower(), part) for part in parts)


def translate_simple_array(value, mapping):
    return join_unique(mapping.get(item, item) for item in parse_array(value))


def translate_phrase(phrase, mapping):
    phrase = phrase.replace("w/", "with ")
    for source in sorted(mapping, key=len, reverse=True):
        phrase = re.sub(rf"\b{re.escape(source)}\b", mapping[source], phrase)
    phrase = phrase.replace(" & ", "/")
    phrase = phrase.replace(", ", "/")
    phrase = re.sub(r"\s+", " ", phrase).strip()
    return phrase


def translate_phrase_array(value, mapping):
    return join_unique(translate_phrase(item, mapping) for item in parse_array(value))


def translate_origin(value, fallback):
    if not value:
        return fallback
    matches = []
    for source, korean in ORIGIN_COUNTRY_MAP.items():
        match = re.search(rf"\b{re.escape(source)}\b", value)
        if match:
            matches.append((match.start(), korean))
    if matches:
        return join_unique(korean for _, korean in sorted(matches))
    if value in ORIGIN_EXACT_MAP:
        return ORIGIN_EXACT_MAP[value]

    translated_parts = []
    changed = False
    for part in [item.strip() for item in value.split(",") if item.strip()]:
        translated = part
        for source in sorted(ORIGIN_TOKEN_MAP, key=len, reverse=True):
            translated = re.sub(rf"\b{re.escape(source)}\b", ORIGIN_TOKEN_MAP[source], translated)
        if translated != part:
            changed = True
        translated_parts.append(translated)

    return ", ".join(translated_parts) if changed else fallback


def main():
    source_rows = read_csv(SOURCE)
    target_rows = read_csv(TARGET)
    source_by_name = {row["matched_breed_name"]: row for row in source_rows}

    for target in target_rows:
        source = source_by_name[target["견종명_영문"]]
        target["견종그룹"] = BREED_GROUP_MAP.get(source.get("dogapi_breed_group", ""), target["견종그룹"])
        target["성격"] = translate_temperament(source.get("dogapi_temperament", ""))
        target["출신"] = BREED_ORIGIN_COUNTRY_MAP.get(
            source["matched_breed_name"],
            translate_origin(source.get("dogapi_origin", ""), target["출신"]),
        )
        target["털_타입"] = translate_simple_array(source.get("akc_coat_type_array", ""), COAT_TYPE_MAP)
        target["털_길이"] = translate_simple_array(source.get("akc_coat_length_array", ""), COAT_LENGTH_MAP)
        target["털_색상"] = translate_phrase_array(source.get("akc_colors_array", ""), COLOR_WORD_MAP)
        target["무늬"] = translate_phrase_array(source.get("akc_markings_array", ""), MARKING_WORD_MAP)

    write_csv(TARGET, target_rows, target_rows[0].keys())
    print(f"Applied mapping dictionary to {len(target_rows)} rows: {TARGET}")


if __name__ == "__main__":
    main()
