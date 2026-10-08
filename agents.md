# Agents — Kovoit Backend

Définitions dans `.claude/agents/`. Tous respectent `CLAUDE.md` (architecture, repository, 200 lignes max, format de réponse) et `PRD.md` (règles métier).

| Agent | Rôle | Écrit du code ? |
|---|---|---|
| `django-architect` | Conçoit une fonctionnalité avant le code : modèles, repository, services, endpoints, découpage < 200 lignes | Non (plan seulement) |
| `django-backend-dev` | Implémente une fonctionnalité : models → migration → repository → services → api → admin | Oui |
| `test-engineer` | Écrit les tests pytest (repository, services, API, concurrence, permissions, Celery) | Oui (tests) |
| `regles-metier-guardian` | Audite la conformité au PRD (statuts, paramètres, prix, code de départ, fiabilité, portefeuille) | Non (rapport) |
| `security-reviewer` | Audite OTP email, JWT, KYC, permissions, IDOR, lien de partage, secrets | Non (rapport) |
| `api-contract-writer` | Tient à jour OpenAPI et `docs/api/` pour le mobile Flutter et l'admin React | Oui (docs) |

## Enchaînement type d'une fonctionnalité

1. `django-architect` → plan validé par l'humain.
2. `django-backend-dev` → implémentation.
3. `test-engineer` → tests.
4. `regles-metier-guardian` + `security-reviewer` → revues (en parallèle).
5. `api-contract-writer` → documentation du contrat.
