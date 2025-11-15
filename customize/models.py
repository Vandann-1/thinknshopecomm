from django.db import models

# Create your models here.
# from django.db import models

class PersonalizedBottle(models.Model):
    name = models.CharField(max_length=100, blank=True)
    custom_text = models.CharField(max_length=200, blank=True)
    birthday_tag = models.CharField(max_length=200, blank=True)
    photo = models.ImageField(upload_to='custom_bottle_photos/', blank=True, null=True)
    bottle_type = models.CharField(max_length=50)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Custom Bottle - {self.name}"
