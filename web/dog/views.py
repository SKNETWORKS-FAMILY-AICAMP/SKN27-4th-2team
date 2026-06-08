from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from .models import DogBreedDictionaryKo
from user.models import DogFavorite
from .services import search_breeds


def get_page(request):
    return render(request, "main/dog.html")


def search(request):
    context = search_breeds(request.GET)
    if request.user.is_authenticated:
        context["favorited_ids"] = set(DogFavorite.objects.filter(user=request.user).values_list("dog_id", flat=True))
    return render(request, "dog/search.html", context)


def detail(request, pk):
    breed = get_object_or_404(DogBreedDictionaryKo, pk=pk)
    
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