from odoo import api, fields, models


class TerrainSurface(models.Model):
    _name = "terrain.surface"
    _description = "Terrain Surface"

    name = fields.Char(required=True, default="New terrain")
    border = fields.GeoPolygon(string="Terrain Border",help="Draw the terrain border manually on the map.")
    surface_m2 = fields.Float(string="Surface (m²)",compute="_compute_surface",store=True,readonly=True,digits=(16, 2))
    surface_hectare = fields.Float(string="Surface (ha)",compute="_compute_surface",store=True,readonly=True,digits=(16, 4))
    note = fields.Text()

    @api.onchange("border")
    def _onchange_border(self):
        self._compute_surface()

    def _get_border_area(self):
        self.ensure_one()
        if not self.border:
            return 0.0
        if hasattr(self.border, "area"):
            return self.border.area
        shape = self._fields["border"].entry_to_shape(self.border)
        return shape.area if shape and not shape.is_empty else 0.0

    @api.depends("border")
    def _compute_surface(self):
        for terrain in self:
            area = terrain._get_border_area()
            terrain.surface_m2 = area
            terrain.surface_hectare = area / 10000.0
