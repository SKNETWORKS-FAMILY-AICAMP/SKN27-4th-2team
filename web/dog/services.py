from django.db.models import Q

from .models import DogBreedDictionaryKo


def get_breed_groups():
    return (
        DogBreedDictionaryKo.objects.exclude(breed_group__isnull=True)
        .exclude(breed_group="")
        .values_list("breed_group", flat=True)
        .distinct()
        .order_by("breed_group")
    )


def get_origins():
    return (
        DogBreedDictionaryKo.objects.exclude(origin__isnull=True)
        .exclude(origin="")
        .values_list("origin", flat=True)
        .distinct()
        .order_by("origin")
    )


def search_breeds(params):
    keyword = (params.get("q") or "").strip()
    group = (params.get("group") or "").strip()
    origin = (params.get("origin") or "").strip()

    breeds = DogBreedDictionaryKo.objects.all()

    if keyword:
        breeds = breeds.filter(
            Q(breed_name_ko__icontains=keyword)
            | Q(breed_name_en__icontains=keyword)
        )

    if group:
        breeds = breeds.filter(breed_group=group)

    if origin:
        breeds = breeds.filter(origin=origin)

    breeds = sorted(
        breeds,
        key=lambda breed: (
            breed.breed_name_ko or "",
            breed.breed_name_en or "",
        ),
    )

    return {
        "breeds": breeds,
        "keyword": keyword,
        "selected_group": group,
        "selected_origin": origin,
        "groups": get_breed_groups(),
        "origins": get_origins(),
    }
