from unittest.mock import patch

from fastapi.testclient import TestClient

import app


def test_matrix_preserves_point_order_and_directed_cells() -> None:
    cells = [
        [{"from_index": 0, "to_index": 0, "time": 0, "distance": 0.0}, {"from_index": 0, "to_index": 1, "time": 50, "distance": 0.4}],
        [{"from_index": 1, "to_index": 0, "time": 40, "distance": 0.3}, {"from_index": 1, "to_index": 1, "time": 0, "distance": 0.0}],
    ]
    with patch.object(app, "_matrix", return_value={"sources_to_targets": cells}) as call:
        response = TestClient(app.app).post(
            "/matrix",
            json={
                "points": [{"lat": 42.5063, "lon": 1.5218}, {"lat": 42.5078, "lon": 1.5211}],
                "costing": "auto",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "units": "kilometers",
        "costing": "auto",
        "sources_to_targets": cells,
    }
    sources, targets, costing = call.call_args.args
    assert [(point.lat, point.lon) for point in sources] == [(42.5063, 1.5218), (42.5078, 1.5211)]
    assert sources == targets
    assert costing == "auto"


def test_matrix_requires_at_least_two_points() -> None:
    with patch.object(app, "_matrix") as call:
        response = TestClient(app.app).post(
            "/matrix",
            json={"points": [{"lat": 42.5063, "lon": 1.5218}]},
        )

    assert response.status_code == 422
    call.assert_not_called()
