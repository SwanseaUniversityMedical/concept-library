from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0115_ontology_search_vector_changes'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- used to derive whether an ontology is a descendant of another
            --
            --      note: takes variadic input(s) in the form of an array for
            --            both the `parents` array and the `queryset` array;
            --            where:
            --               `parents` - defines the `parent_id` ref(s)
            --               `queryset` - defines the `child_id` ref(s)
            --

            create or replace function is_ontological_descendant(parents bigint[], queryset bigint[]) returns boolean
            language plpgsql strict as $bd$
			declare
				is_descendant boolean;
            begin

                with recursive traversal(child_id, parent_id, depth, path) as (
                    select
                            first.child_id,
                            first.parent_id,
                            1 as depth,
                            array[first.child_id] as path
                      from public.clinicalcode_ontologytagedge as first
                     where first.child_id = any(queryset)
                     union all
                    select
                            first.child_id,
                            first.parent_id,
                            second.depth + 1 as depth,
                            path || first.child_id as path
                      from
                            public.clinicalcode_ontologytagedge as first,
                            traversal as second
                     where first.child_id = second.parent_id
                       and first.child_id <> ALL(second.path)
                       and first.parent_id = any(parents)
                )
				
				
				select exists(
					select 1
					  from traversal t0
					 where t0.parent_id = any(parents)
				)
				limit 1
				into is_descendant;

				return is_descendant;
            end;
            $bd$;
            
            """,
            reverse_sql="""
            drop function if exists is_ontological_descendant;
            """
        ),
    ]
