from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Création des utilisateurs. L'email est l'identifiant de connexion, toujours en minuscules."""

    use_in_migrations = True

    def create_user(self, email, password=None, **champs):
        if not email:
            raise ValueError("L'email est obligatoire.")
        utilisateur = self.model(email=email.strip().lower(), **champs)
        if password:
            utilisateur.set_password(password)
        else:
            utilisateur.set_unusable_password()
        utilisateur.save(using=self._db)
        return utilisateur

    def create_superuser(self, email, password, **champs):
        champs.update(is_staff=True, is_superuser=True, email_verifie=True)
        return self.create_user(email, password, **champs)
