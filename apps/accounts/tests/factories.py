import factory

from apps.accounts.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"utilisateur{n}@exemple.tg")
    telephone = factory.Sequence(lambda n: f"+2289{n:07d}")
    nom = "Amegah"
    prenom = "Kossi"
    email_verifie = True
