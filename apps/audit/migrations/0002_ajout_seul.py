"""Protection en base du journal d'audit (PostgreSQL) : UPDATE toujours refusé, DELETE refusé
sauf pendant une purge contrôlée (variable de session kovoit.audit_purge, voir repository.py).

Ce n'est pas une protection absolue : le propriétaire de la base peut retirer le trigger. Elle
empêche en revanche toute modification par le code applicatif, le Django admin ou une erreur.
"""

from django.db import migrations

CREER = """
CREATE OR REPLACE FUNCTION audit_ajout_seul() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' AND current_setting('kovoit.audit_purge', true) = 'on' THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION 'Journal d''audit en ajout seul : % interdit', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_ajout_seul
BEFORE UPDATE OR DELETE ON audit_evenementaudit
FOR EACH ROW EXECUTE FUNCTION audit_ajout_seul();
"""

SUPPRIMER = """
DROP TRIGGER IF EXISTS audit_ajout_seul ON audit_evenementaudit;
DROP FUNCTION IF EXISTS audit_ajout_seul();
"""


def creer(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(CREER, params=None)


def supprimer(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(SUPPRIMER, params=None)


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]

    operations = [migrations.RunPython(creer, supprimer)]
