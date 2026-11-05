import factory
from django.contrib.auth.models import Group

from apps.accounts.models import User
from apps.accounts.roles import ROLES


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"utilisateur{n}@exemple.tg")
    telephone = factory.Sequence(lambda n: f"+2289{n:07d}")
    nom = "Amegah"
    prenom = "Kossi"
    email_verifie = True


class AdminFactory(UserFactory):
    """Admin (is_staff) doté par défaut des quatre rôles ; `roles=[]` : admin sans rôle."""

    is_staff = True
    prenom = "Admin"

    @factory.post_generation
    def roles(self, create, extracted, **kwargs):
        if not create:
            return
        noms = list(ROLES) if extracted is None else list(extracted)
        self.groups.set([Group.objects.get_or_create(name=nom)[0] for nom in noms])
