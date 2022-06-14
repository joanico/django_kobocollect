from django.db import models

class Beneficiary(models.Model):
    bene_id = models.IntegerField(blank = True, null = True)
    name = models.CharField(max_length=100, blank = True, null = True)
    date = models.DateTimeField(blank = True, null = True)
    municipality = models.CharField(max_length=100, blank = True, null = True)
    postadmin = models.CharField(max_length=100, blank = True, null = True)
    suco = models.CharField(max_length=100, blank = True, null = True)

    def __str__(self):
        return self.name


class Municipality(models.Model): 
    name = models.CharField(max_length=100, blank=True, null=True)

class PostAdmin(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    municipality = models.ForeignKey('Municipality', on_delete=models.CASCADE)

class Suco(models.Model):
    name = models.CharField(max_length=100, blank = True, null = True)
    postadmin = models.ForeignKey('PostAdmin', on_delete=models.CASCADE)
