from odoo import fields, models


class GeoRasterLayer(models.Model):
    _inherit = "geoengine.raster.layer"

    raster_type = fields.Selection(
        selection_add=[("arcgis_xyz", "ArcGIS XYZ tiles")],
        ondelete={"arcgis_xyz": "cascade"},
    )
