from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('geoserver', '0004_auto_20200514_1522'),
    ]

    drop_if_exists = "drop view if exists geoserver_shipinfosview;"
    create_view_sql = """
create view geoserver_shipinfosview as
    select infos.*,
            shiptype.short_name as type_shortname,
            shiptype.summary as type_summary,
            geometries.width,
            geometries.height,
            geometries.wkt_shape
        from core_shipinfos as infos
        left outer join geoserver_shipgeometries as geometries
            on infos.mmsi = geometries.mmsi
        left outer join core_shiptype as shiptype
            on infos.ship_type = shiptype.type_id
"""

    operations = [
        migrations.RunSQL(drop_if_exists),
        migrations.RunSQL(create_view_sql),
    ]
