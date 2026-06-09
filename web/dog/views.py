from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from .models import DogBreedDictionaryKo
from user.models import DogFavorite
from .services import search_breeds


def _should_rotate_breed_image(breed):
    return (
        breed.breed_name_ko in {"시추", "시츄", "플롯 하운드"}
        or breed.breed_name_en in {"Shih Tzu", "Plott Hound"}
    )


def search(request):
    context = search_breeds(request.GET)
    paginator = Paginator(context["breeds"], 8)
    page_obj = paginator.get_page(request.GET.get("page"))
    breeds = list(page_obj.object_list)
    for breed in breeds:
        breed.rotate_image_90 = _should_rotate_breed_image(breed)
    query_params = request.GET.copy()
    query_params.pop("page", None)

    context["breeds"] = breeds
    context["page_obj"] = page_obj
    context["paginator"] = paginator
    context["page_range"] = paginator.get_elided_page_range(
        number=page_obj.number,
        on_each_side=1,
        on_ends=1,
    )
    context["query_string"] = query_params.urlencode()
    context["total_count"] = paginator.count
    context["visible_start"] = page_obj.start_index() if paginator.count else 0
    context["visible_end"] = page_obj.end_index() if paginator.count else 0

    if request.user.is_authenticated:
        context["favorited_ids"] = set(DogFavorite.objects.filter(user=request.user).values_list("dog_id", flat=True))
    return render(request, "dog/search.html", context)


def detail(request, pk):
    breed = get_object_or_404(DogBreedDictionaryKo, pk=pk)
    breed.rotate_image_90 = _should_rotate_breed_image(breed)
    
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = DogFavorite.objects.filter(user=request.user, dog=breed).exists()
        
    return render(request, "dog/detail.html", {
        "breed": breed,
        "is_favorited": is_favorited
    })

@login_required
def toggle_favorite(request, pk):
    if request.method == "POST":
        breed = get_object_or_404(DogBreedDictionaryKo, pk=pk)
        favorite, created = DogFavorite.objects.get_or_create(user=request.user, dog=breed)
        
        if not created:
            favorite.delete()
            is_favorited = False
        else:
            is_favorited = True
            
        return JsonResponse({"status": "success", "is_favorited": is_favorited})
    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)
