# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import random
import string

from odoo.tools import SQL, Query
from odoo.orm import domains
from odoo.orm.utils import SQL_OPERATORS

from .fields import GeoField
from .geo_operators import GeoOperator

GEO_OPERATORS = {
    "geo_greater": ">",
    "geo_lesser": "<",
    "geo_equal": "=",
    "geo_touch": "ST_Touches",
    "geo_within": "ST_Within",
    "geo_contains": "ST_Contains",
    "geo_intersect": "ST_Intersects",
}
GEO_SQL_OPERATORS = {
    "geo_greater": SQL(">"),
    "geo_lesser": SQL("<"),
    "geo_equal": SQL("="),
    "geo_touch": SQL("ST_Touches"),
    "geo_within": SQL("ST_Within"),
    "geo_contains": SQL("ST_Contains"),
    "geo_intersect": SQL("ST_Intersects"),
}
SQL_OPERATORS.update(GEO_SQL_OPERATORS)
domains.CONDITION_OPERATORS.update(GEO_OPERATORS)
domains.STANDARD_CONDITION_OPERATORS = domains.STANDARD_CONDITION_OPERATORS | set(
    GEO_OPERATORS
)


def _condition_to_sql(
    self, field_expr: str, operator: str, value, model, alias: str, query: Query
) -> SQL:
    """
    This method has been monkey patched on GeoField in order to be able to
    include geo_operators into the Odoo search method.
    """
    if operator in GEO_OPERATORS.keys():
        current_operator = GeoOperator(self)
        params = []
        if isinstance(value, dict):
            # We are having indirect geo_operator like ('geom', 'geo_...',
            # {'res.zip.poly': [('id', 'in', [1, 2, 3])]})
            ref_search = value
            sub_queries = []
            for key in ref_search:
                i = key.rfind(".")
                rel_model_name = key[0:i]
                rel_col = key[i + 1 :]
                rel_model = model.env[rel_model_name]
                # we compute the attributes search on spatial rel
                if ref_search[key]:
                    rel_alias = (
                        rel_model._table
                        + "_"
                        + "".join(random.choices(string.ascii_lowercase, k=5))
                    )
                    rel_query = where_calc(
                        rel_model,
                        ref_search[key],
                        active_test=True,
                        alias=rel_alias,
                    )
                    rel_model._apply_ir_rules(rel_query, "read")
                    if operator == "geo_equal":
                        rel_query.add_where(
                            SQL(
                                "%s %s %s",
                                model._field_to_sql(alias, field_expr, query),
                                GEO_SQL_OPERATORS[operator],
                                SQL.identifier(rel_alias, rel_col),
                            )
                        )
                    elif operator in ("geo_greater", "geo_lesser"):
                        rel_query.add_where(
                            SQL(
                                "ST_Area(%s) %s ST_Area(%s)",
                                model._field_to_sql(alias, field_expr, query),
                                GEO_SQL_OPERATORS[operator],
                                SQL.identifier(rel_alias, rel_col),
                            )
                        )
                    else:
                        rel_query.add_where(
                            SQL(
                                "%s(%s, %s)",
                                GEO_SQL_OPERATORS[operator],
                                model._field_to_sql(alias, field_expr, query),
                                SQL.identifier(rel_alias, rel_col),
                            )
                        )

                    sub_queries.append(SQL("EXISTS (%s)", rel_query.subselect("1")))
            sql = SQL(" AND ").join(sub_queries)
        else:
            sql = get_geo_func(
                current_operator, operator, field_expr, value, params, alias
            )
            return SQL(sql, *params)
        return sql
    return super(GeoField, self).condition_to_sql(
        field_expr, operator, value, model, alias, query
    )


def get_geo_func(current_operator, operator, left, value, params, table):
    """
    This method will call the SQL query corresponding to the requested geo operator
    """
    match operator:
        case "geo_greater":
            query = current_operator.get_geo_greater_sql(table, left, value, params)
        case "geo_lesser":
            query = current_operator.get_geo_lesser_sql(table, left, value, params)
        case "geo_equal":
            query = current_operator.get_geo_equal_sql(table, left, value, params)
        case "geo_touch":
            query = current_operator.get_geo_touch_sql(table, left, value, params)
        case "geo_within":
            query = current_operator.get_geo_within_sql(table, left, value, params)
        case "geo_contains":
            query = current_operator.get_geo_contains_sql(table, left, value, params)
        case "geo_intersect":
            query = current_operator.get_geo_intersect_sql(table, left, value, params)
        case _:
            raise NotImplementedError(f"The operator {operator} is not supported")
    return query


def where_calc(model, domain, active_test=True, alias=None):
    """
    This method mirrors Odoo's native _search domain-to-query path while
    allowing callers to force a table alias for indirect geo operators.
    """
    domain = domains.Domain(domain)
    if (
        model._active_name
        and active_test
        and model.env.context.get("active_test", True)
        and not any(
            condition.field_expr == model._active_name
            for condition in domain.iter_conditions()
        )
    ):
        domain &= domains.Domain(model._active_name, "=", True)

    table_alias = alias or model._table
    query = Query(model.env, table_alias, model._table)
    domain = domain.optimize_full(model)
    if not domain.is_true():
        query.add_where(domain._to_sql(model, table_alias, query))
    return query

GeoField.condition_to_sql = _condition_to_sql
