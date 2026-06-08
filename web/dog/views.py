from django.shortcuts import get_object_or_404, render

from .models import DogBreedDictionaryKo
from .services import search_breeds


def get_page(request):
    return render(request, "main/dog.html")


def search(request):
    context = search_breeds(request.GET)
    return render(request, "dog/search.html", context)


def detail(request, pk):
    breed = get_object_or_404(DogBreedDictionaryKo, pk=pk)
    return render(request, "dog/detail.html", {"breed": breed})