from django.db import migrations

# Agent identity D9, D10: a matricule never changes and an agent is never
# deleted, so a matricule is never reused (SOC-01). TRUNCATE stays possible: the
# test runner empties tables with it, and only the table owner may run it.
TRIGGERS_SQL = """
CREATE FUNCTION agents_refuse_matricule_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.matricule IS DISTINCT FROM OLD.matricule THEN
        RAISE EXCEPTION 'Le matricule d''un agent ne peut pas être modifié.'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER agents_agent_matricule_fixe
    BEFORE UPDATE ON agents_agent
    FOR EACH ROW EXECUTE FUNCTION agents_refuse_matricule_change();

CREATE FUNCTION agents_refuse_delete() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Un agent n''est jamais supprimé.'
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$;
CREATE TRIGGER agents_agent_jamais_supprime
    BEFORE DELETE ON agents_agent
    FOR EACH ROW EXECUTE FUNCTION agents_refuse_delete();
"""

DROP_SQL = """
DROP TRIGGER agents_agent_jamais_supprime ON agents_agent;
DROP FUNCTION agents_refuse_delete();
DROP TRIGGER agents_agent_matricule_fixe ON agents_agent;
DROP FUNCTION agents_refuse_matricule_change();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("agents", "0001_initial"),
    ]

    operations = [migrations.RunSQL(TRIGGERS_SQL, DROP_SQL)]
