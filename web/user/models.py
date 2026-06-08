from django.conf import settings
from django.db import models


class Pet(models.Model):
    """사용자가 마이페이지에 등록하는 반려동물 정보입니다."""

    # DB에는 왼쪽 값(dog/cat/other)이 저장되고, 화면에는 오른쪽 한글이 표시됩니다.
    SPECIES_CHOICES = [
        ('dog', '강아지'),
        ('cat', '고양이'),
        ('other', '기타'),
    ]

    GENDER_CHOICES = [
        ('unknown', '모름'),
        ('male', '남아'),
        ('female', '여아'),
    ]

    # settings.AUTH_USER_MODEL은 현재 프로젝트에서 사용하는 User 모델을 뜻합니다.
    # on_delete=models.CASCADE는 사용자가 삭제되면 연결된 반려동물도 같이 삭제한다는 의미입니다.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pets')
    name = models.CharField(max_length=50)
    species = models.CharField(max_length=20, choices=SPECIES_CHOICES, default='dog')
    breed = models.CharField(max_length=80, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default='unknown')
    memo = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # 마이페이지에서 최근 수정한 반려동물이 위에 보이도록 정렬합니다.
        ordering = ['-updated_at']

    def __str__(self):
        # Django 관리자 화면이나 shell에서 객체를 볼 때 표시되는 이름입니다.
        return f'{self.name} ({self.user})'


class DogFavorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dog_favorites')
    dog = models.ForeignKey('dog.DogBreedDictionaryKo', on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'dog')

    def __str__(self):
        return f"{self.user} - {self.dog}"


class ShelterFavorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shelter_favorites')
    shelter_animal = models.ForeignKey('shelter.ShelterAnimal', on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'shelter_animal')

    def __str__(self):
        return f"{self.user} - {self.shelter_animal}"
