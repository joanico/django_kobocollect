from django.db import models

class Beneficiary(models.Model):
    name = models.CharField(max_length=100)
    date = models.DateTimeField()

    def __str__(self):
        return self.name

class Municipality(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class PostAdmin(models.Model):
    name = models.CharField(max_length=100)
    municipality = models.ForeignKey(Municipality, on_delete = models.SET_NULL, null =True)

    def __str__(self):
        return self.name

class Suco(models.Model):
    name = models.CharField(max_length=100)
    postadmin = models.ForeignKey(PostAdmin, on_delete = models.SET_NULL, null =True)

    def __str__(self):
        return self.name
