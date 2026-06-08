from django.db import models


class DogBreedDictionaryKo(models.Model):
    breed_name_en = models.CharField(max_length=150, unique=True)
    breed_name_ko = models.CharField(max_length=150)
    breed_group = models.CharField(max_length=100, null=True, blank=True)
    breed_group_number = models.IntegerField(null=True, blank=True)
    breed_group_description = models.TextField(null=True, blank=True)
    temperament = models.TextField(null=True, blank=True)
    origin = models.CharField(max_length=200, null=True, blank=True)
    image_url = models.TextField(null=True, blank=True)

    height_min_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    height_max_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    weight_min_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    weight_max_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    life_expectancy_min = models.IntegerField(null=True, blank=True)
    life_expectancy_max = models.IntegerField(null=True, blank=True)
    affectionate_with_family_score = models.IntegerField(null=True, blank=True)
    good_with_young_children_score = models.IntegerField(null=True, blank=True)
    good_with_other_dogs_score = models.IntegerField(null=True, blank=True)
    shedding_level_score = models.IntegerField(null=True, blank=True)
    grooming_needs_score = models.IntegerField(null=True, blank=True)
    drooling_level_score = models.IntegerField(null=True, blank=True)
    openness_to_strangers_score = models.IntegerField(null=True, blank=True)
    playfulness_level_score = models.IntegerField(null=True, blank=True)
    watchdog_score = models.IntegerField(null=True, blank=True)
    adaptability_score = models.IntegerField(null=True, blank=True)
    trainability_score = models.IntegerField(null=True, blank=True)
    energy_level_score = models.IntegerField(null=True, blank=True)
    barking_level_score = models.IntegerField(null=True, blank=True)
    mental_stimulation_needs_score = models.IntegerField(null=True, blank=True)

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

    @property
    def size_category(self):
        if self.weight_max_kg is None:
            return "크기 미상"
        elif self.weight_max_kg < 10:
            return "소형견"
        elif self.weight_max_kg < 25:
            return "중형견"
        else:
            return "대형견"