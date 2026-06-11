from django.db import models


class ShelterAnimal(models.Model):
    desertion_no = models.CharField(max_length=50, unique=True)
    notice_no = models.CharField(max_length=100, blank=True, null=True)
    happen_dt = models.DateField(blank=True, null=True)
    happen_place = models.TextField(blank=True, null=True)
    up_kind_cd = models.CharField(max_length=20, blank=True, null=True)
    up_kind_nm = models.CharField(max_length=50, blank=True, null=True)
    kind_cd = models.CharField(max_length=20, blank=True, null=True)
    kind_nm = models.CharField(max_length=150, blank=True, null=True)
    kind_full_nm = models.CharField(max_length=200, blank=True, null=True)
    color_cd = models.CharField(max_length=100, blank=True, null=True)
    age = models.CharField(max_length=100, blank=True, null=True)
    weight = models.CharField(max_length=100, blank=True, null=True)
    sex_cd = models.CharField(max_length=10, blank=True, null=True)
    neuter_yn = models.CharField(max_length=10, blank=True, null=True)
    special_mark = models.TextField(blank=True, null=True)
    care_reg_no = models.CharField(max_length=50, blank=True, null=True)
    care_nm = models.CharField(max_length=200, blank=True, null=True)
    care_tel = models.CharField(max_length=100, blank=True, null=True)
    care_addr = models.TextField(blank=True, null=True)
    care_owner_nm = models.CharField(max_length=200, blank=True, null=True)
    org_nm = models.CharField(max_length=200, blank=True, null=True)
    notice_sdt = models.DateField(blank=True, null=True)
    notice_edt = models.DateField(blank=True, null=True)
    process_state = models.CharField(max_length=100, blank=True, null=True)
    popfile1 = models.TextField(blank=True, null=True)
    popfile2 = models.TextField(blank=True, null=True)
    api_updated_at = models.DateTimeField(blank=True, null=True)
    fetched_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "shelter_animals"
        ordering = ["-notice_sdt", "-id"]

    @property
    def sex_label(self) -> str:
        return {"M": "수컷", "F": "암컷", "Q": "미상"}.get(self.sex_cd or "", "미상")

    @property
    def neuter_label(self) -> str:
        return {"Y": "예", "N": "아니오", "U": "미상"}.get(self.neuter_yn or "", "미상")
