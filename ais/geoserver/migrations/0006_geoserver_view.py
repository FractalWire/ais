from django.db import migrations
from core.models import ShipInfos


class Migration(migrations.Migration):

    dependencies = [
        ('geoserver', '0005_auto_20200514_1853'),
    ]

    drop_if_exists = "drop view if exists geoserver_shipinfosview;"
    create_view_sql = """
create view geoserver_shipinfosview as
    select infos.*,
            coalesce(shiptype.short_name, '{0}') as type_shortname,
            coalesce(shiptype.summary, '{0}') as type_summary,
            coalesce(geometries.length, {1}) as length,
            coalesce(geometries.width, {2}) as width,
            coalesce(geometries.wkt_shape, '{3}') as wkt_shape
        from core_shipinfos as infos
        left outer join geoserver_shipgeometries as geometries
            on infos.mmsi = geometries.mmsi
        left outer join core_shiptype as shiptype
            on infos.ship_type = shiptype.type_id;
""".format(
        'unspecified',
        ShipInfos.DEFAULT_LENGTH,
        ShipInfos.DEFAULT_WIDTH,
        ShipInfos.DEFAULT_WKT
    )

    operations = [
        migrations.RunSQL(drop_if_exists, drop_if_exists),
        migrations.RunSQL(create_view_sql, drop_if_exists),
    ]
