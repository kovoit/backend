# Kovoit — Backend

API Django REST du MVP Kovoit (covoiturage urbain à Lomé), consommée par l'app mobile Flutter et l'admin React.

- Règles métier : [PRD.md](PRD.md)
- Règles techniques, architecture et commandes : [claude.md](claude.md)
- Agents Claude Code : [agents.md](agents.md)

## Démarrage rapide (Windows)

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cp .env.example .env            # renseigner DJANGO_SECRET_KEY (et Gmail pour l'envoi réel d'emails)
docker compose up -d db redis
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py seed_parametres
.venv/Scripts/python manage.py createsuperuser
.venv/Scripts/python manage.py runserver
```

- Santé de l'API : http://localhost:8000/api/v1/sante/
- Documentation Swagger : http://localhost:8000/api/docs/
- Django admin : http://localhost:8000/django-admin/

Toutes les réponses suivent le format :

```json
{ "statut": "success", "message": "…", "reponse": { } }
```

## Tester un trajet complet avec deux téléphones

Le mobile ne simule jamais l'autre rôle.
Le parcours conducteur ↔ passager se teste sur le vrai backend, avec deux comptes et deux téléphones.
Il n'y a pas de bouton dans l'app pour avancer le temps : on utilise la commande `avancer_trajet`.

### Préparer

1. Mettre `DJANGO_DEBUG=True` dans `.env` (obligatoire pour `seed_comptes_test` et `avancer_trajet`).
2. Créer les comptes de test : `python manage.py seed_comptes_test`.
   - `conducteur.verifie@kovoit.test` : publie un trajet (KYC et véhicule validés).
   - `passager.verifie@kovoit.test` : réserve.
   - Le mot de passe est affiché par la commande.
3. Lancer l'API joignable sur le Wi-Fi :
   `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,<IP du PC> python manage.py runserver 0.0.0.0:8000`.
4. Lancer l'app sur chaque téléphone avec le vrai backend :
   `flutter run --dart-define=USE_MOCK_API=false --dart-define=API_BASE_URL=http://<IP du PC>:8000/api/v1`.
5. Téléphone A : se connecter en conducteur. Téléphone B : se connecter en passager.

### Avancer le temps : `avancer_trajet`

```bash
python manage.py avancer_trajet                  # dernier trajet non clos, jusqu'à l'heure de départ
python manage.py avancer_trajet <trajet_id>      # ce trajet, jusqu'à l'heure de départ
python manage.py avancer_trajet --minutes 10     # avance de 10 min
python manage.py avancer_trajet <trajet_id> --heures 3
```

- Réservée au développement : sans `DJANGO_DEBUG=True`, la commande s'arrête en erreur.
- Sans `trajet_id` : dernier trajet créé encore publié, complet ou en cours.
- Sans durée : avance jusqu'à l'heure de départ (à la minute près).
- `--minutes` et `--heures` ne se combinent pas. Minimum : 1 minute.
  Maximum : `periode_incidents_j` jours (30 par défaut) ;
  au-delà, la fiabilité et les économies du mois seraient faussées.
- Départ déjà passé et aucune durée donnée : rien n'est reculé.
  La commande affiche « Départ déjà passé : utilisez --minutes ou --heures » et lance quand même les tâches.
- L'horloge du serveur ne change pas. La commande recule les horaires d'un seul trajet :
  son départ (`depart_le`), sa dernière position (`position_le`),
  la création et chaque horodatage de statut de ses réservations.
- Elle lance ensuite tout de suite l'expiration (`expirer_reservations`)
  et la clôture automatique (`cloturer_automatiquement`), sans attendre Celery beat.
- L'expiration et la clôture lancées sont globales : elles traitent toute la base, comme Celery beat,
  pas seulement ce trajet.
- Le recul n'est pas journalisé dans l'audit (outil de dev, comme les commandes `seed_*`).
- Elle affiche l'id du trajet, le nouveau départ, le nombre de réservations expirées et clôturées,
  et la valeur actuelle des délais ci-dessous.

### Délais utiles

| Paramètre | Valeur de départ | Effet |
|---|---|---|
| `tolerance_retard_min` | 10 min | Absence déclarable seulement après départ + ce délai |
| `delai_confirmation_auto_h` | 3 h | Clôture automatique ce délai après la fin du trajet |
| `delai_resolution_h` | 6 h | Réservation acceptée sans code ni absence : annulée ce délai après le départ |

Ces valeurs viennent de `seed_parametres` (`apps/parametres/defauts.py`).
Elles se modifient dans les paramètres : écran Paramètres du back-office React,
ou Django admin (`/django-admin/`). La commande affiche toujours la valeur en base.

### Scénario

1. **Conducteur** (téléphone A) : publie un trajet.
2. **Passager** (téléphone B) : recherche le trajet et réserve une place.
3. **Conducteur** : accepte la demande.
   Une demande encore sans réponse à l'heure de départ est refusée automatiquement.
4. **PC** : `python manage.py avancer_trajet` (jusqu'au départ).
   Noter l'id du trajet affiché : il sert à l'étape 7.
5. **Conducteur** : au choix
   - saisit le code de départ affiché sur le téléphone du passager ;
   - ou déclare le passager absent. Il faut d'abord dépasser la tolérance :
     `python manage.py avancer_trajet --minutes 10` (valeur de `tolerance_retard_min`).
6. **Conducteur** : termine le trajet.
7. **PC** : `python manage.py avancer_trajet <trajet_id> --heures 3`
   (valeur de `delai_confirmation_auto_h`).
   L'id est obligatoire ici : un trajet terminé n'est plus choisi par défaut.
8. **Résultat** : la réservation passe en « clôturée » et le conducteur est payé.
   Le passager peut aussi confirmer son arrivée avant, ce qui clôture tout de suite.
   Cas de l'absence : la réservation reste « absent » (le passager a déjà payé), rien à clôturer.

Attention : ne pas avancer de 6 h ou plus (`delai_resolution_h`) avant l'étape 5.
Sinon la réservation acceptée est annulée et le montant débloqué.
