from __future__ import annotations

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import DatabaseError, ProgrammingError
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from .models import ShelterAnimal
from user.models import ShelterFavorite


DEFAULT_STATUS = "보호중"
ADOPTED_STATUS = "종료(입양)"
PAGE_SIZE = 9
OPTION_LIMIT = 300


def _animal_to_card(animal: ShelterAnimal) -> dict[str, str]:
    return {
        "id": animal.id,
        "desertion_no": animal.desertion_no,
        "breed": animal.kind_nm or animal.kind_full_nm or "품종 미상",
        "age": animal.age or "나이 미상",
        "sex": animal.sex_label,
        "neutered": animal.neuter_label,
        "image_url": animal.popfile1 or animal.popfile2 or "",
        "shelter_name": animal.care_nm or "보호소 정보 없음",
        "shelter_tel": animal.care_tel or "",
        "shelter_address": animal.care_addr or "",
        "region": animal.org_nm or "",
        "notice_start_date": animal.notice_sdt.strftime("%Y.%m.%d") if animal.notice_sdt else "",
        "notice_end_date": animal.notice_edt.strftime("%Y.%m.%d") if animal.notice_edt else "",
        "status": animal.process_state or "상태 미상",
        "happen_place": animal.happen_place or "-",
        "special_mark": animal.special_mark or "-",
    }


def _option_values(field_name: str) -> list[str]:
    values = (
        ShelterAnimal.objects.exclude(**{f"{field_name}__isnull": True})
        .exclude(**{field_name: ""})
        .values_list(field_name, flat=True)
        .distinct()
        .order_by(field_name)[:OPTION_LIMIT]
    )
    return list(values)


def _filtered_base_queryset(breed: str, region: str):
    queryset = ShelterAnimal.objects.all()

    if breed:
        queryset = queryset.filter(kind_nm=breed)
    if region:
        queryset = queryset.filter(org_nm=region)

    return queryset


def shelter_animals_page(request):
    breed = request.GET.get("breed", "").strip()
    region = request.GET.get("region", "").strip()
    status = request.GET.get("status", DEFAULT_STATUS).strip()

    animals = []
    animal_count = 0
    total_animal_count = 0
    protecting_count = 0
    adopted_count = 0
    other_status_count = 0
    page_obj = None
    page_range = []
    query_string = ""
    breed_options: list[str] = []
    region_options: list[str] = []
    status_options: list[str] = []
    error_message = ""

    try:
        breed_options = _option_values("kind_nm")
        region_options = _option_values("org_nm")
        status_options = _option_values("process_state")

        base_queryset = _filtered_base_queryset(breed, region)
        total_animal_count = base_queryset.count()
        protecting_count = base_queryset.filter(process_state=DEFAULT_STATUS).count()
        adopted_count = base_queryset.filter(process_state=ADOPTED_STATUS).count()
        other_status_count = total_animal_count - protecting_count - adopted_count

        queryset = base_queryset
        if status:
            queryset = queryset.filter(process_state=status)

        animal_count = queryset.count()
        query_params = request.GET.copy()
        query_params.pop("page", None)
        query_string = query_params.urlencode()

        if animal_count:
            paginator = Paginator(queryset, PAGE_SIZE)
            page_number = request.GET.get("page", 1)

            try:
                page_obj = paginator.page(page_number)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)

            current_page = page_obj.number
            start_page = max(current_page - 2, 1)
            end_page = min(current_page + 2, paginator.num_pages)
            page_range = range(start_page, end_page + 1)
            animals = [_animal_to_card(animal) for animal in page_obj.object_list]
    except (DatabaseError, ProgrammingError) as exc:
        error_message = (
            "보호동물 DB를 아직 조회할 수 없습니다. "
            "shelter_animals 적재가 끝났는지 확인해 주세요. "
            f"({exc})"
        )

    favorited_ids = set()
    if request.user.is_authenticated:
        favorited_ids = set(request.user.shelter_favorites.values_list("shelter_animal_id", flat=True))

    context = {
        "breed": breed,
        "region": region,
        "status": status,
        "animals": animals,
        "animal_count": animal_count,
        "total_animal_count": total_animal_count,
        "protecting_count": protecting_count,
        "adopted_count": adopted_count,
        "other_status_count": other_status_count,
        "visible_count": len(animals),
        "page_size": PAGE_SIZE,
        "page_obj": page_obj,
        "page_range": page_range,
        "query_string": query_string,
        "error_message": error_message,
        "breed_options": breed_options,
        "region_options": region_options,
        "status_options": status_options,
        "favorited_ids": favorited_ids,
    }

    if request.GET.get("ajax") == "true":
        from django.template.loader import render_to_string
        html = render_to_string("shelter/_animal_list.html", context, request=request)
        return JsonResponse({
            "status": "success",
            "html": html,
            "animal_count": animal_count,
            "total_animal_count": total_animal_count,
            "protecting_count": protecting_count,
            "adopted_count": adopted_count,
            "other_status_count": other_status_count,
            "visible_count": len(animals),
            "breed": breed,
        })

    return render(
        request,
        "shelter/list.html",
        context,
    )


@login_required
def toggle_favorite(request, pk):
    if request.method == "POST":
        animal = get_object_or_404(ShelterAnimal, pk=pk)
        favorite, created = ShelterFavorite.objects.get_or_create(user=request.user, shelter_animal=animal)
        
        if not created:
            favorite.delete()
            is_favorited = False
        else:
            is_favorited = True
            
        return JsonResponse({"status": "success", "is_favorited": is_favorited})
    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)




