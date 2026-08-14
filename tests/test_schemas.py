"""Unit tests for CALL-E result schema definitions."""

from hungrycall.models import Mode
from hungrycall.schemas import (
    DELIVERY_RESULT_SCHEMA,
    PICKUP_RESULT_SCHEMA,
    RESERVATION_RESULT_SCHEMA,
    get_result_schema,
)


def test_get_result_schema_types():
    deliv_schema = get_result_schema(Mode.DELIVERY)
    assert deliv_schema == DELIVERY_RESULT_SCHEMA
    assert "delivers_to_address" in deliv_schema["required"]
    assert "price_known" in deliv_schema["required"]
    assert "total_price_eur" in deliv_schema["properties"]

    res_schema = get_result_schema(Mode.RESERVATION)
    assert res_schema == RESERVATION_RESULT_SCHEMA
    assert "table_available" in res_schema["required"]
    assert "reservation_confirmed" in res_schema["required"]

    pickup_schema = get_result_schema(Mode.PICKUP)
    assert pickup_schema == PICKUP_RESULT_SCHEMA
    assert "pickup_available" in pickup_schema["required"]
    assert "price_known" in pickup_schema["required"]
