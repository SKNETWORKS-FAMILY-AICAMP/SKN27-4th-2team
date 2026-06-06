from django.db import models


class DogBreedDictionaryKo(models.Model):
    breed_name_en = models.CharField(max_length=150, unique=True)
    breed_name_ko = models.CharField(max_length=150)
    breed_group = models.CharField(max_length=100, null=True, blank=True)
    temperament = models.TextField(null=True, blank=True)
    origin = models.CharField(max_length=200, null=True, blank=True)
    image_url = models.TextField(null=True, blank=True)

    height_min_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    height_max_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    weight_min_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    weight_max_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    life_expectancy_min = models.IntegerField(null=True, blank=True)
    life_expectancy_max = models.IntegerField(null=True, blank=True)

    about = models.TextField(null=True, blank=True)
    health = models.TextField(null=True, blank=True)
    grooming = models.TextField(null=True, blank=True)
    exercise = models.TextField(null=True, blank=True)
    training = models.TextField(null=True, blank=True)
    nutrition = models.TextField(null=True, blank=True)
    history = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "dog_breed_dictionary_ko"
        ordering = ["breed_name_ko", "breed_name_en"]

    def __str__(self):
        return self.breed_name_ko or self.breed_name_en