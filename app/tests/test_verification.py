
from app.services.verification import verify_hypotheses


def test_database_hypothesis_is_supported_by_matching_logs():
    hypotheses = [
        {
            "cause": "Database connection saturation",
            "confidence": 0.85,
            "evidence": ["Database connection timeout"],
        }
    ]

    evidence = {
        "logs": {
            "findings": [
                {"category": "database_connection_saturation"}
            ]
        },
        "metrics": {"findings": []},
        "deployment": {"recent_deployment": False},
    }

    result = verify_hypotheses(hypotheses, evidence)

    assert result[0]["verification_status"] == "supported"
    assert result[0]["missing_evidence"]


def test_database_hypothesis_is_inconclusive_without_matching_logs():
    hypotheses = [
        {
            "cause": "Database connection saturation",
            "confidence": 0.85,
            "evidence": [],
        }
    ]

    evidence = {
        "logs": {"findings": []},
        "metrics": {"findings": []},
        "deployment": {"recent_deployment": False},
    }

    result = verify_hypotheses(hypotheses, evidence)

    assert result[0]["verification_status"] == "inconclusive"



def test_latency_hypothesis_is_supported_by_latency_metric():
    hypotheses = [
        {
            "cause": "Elevated application latency",
            "confidence": 0.60,
            "evidence": ["Reported latency is 1800 ms."],
        }
    ]

    evidence = {
        "logs": {"findings": []},
        "metrics": {
            "findings": [
                {
                    "metric": "latency_ms",
                    "value": 1800,
                    "threshold": 1000,
                    "observation": "Response latency is elevated.",
                }
            ]
        },
        "deployment": {"recent_deployment": False},
    }

    result = verify_hypotheses(hypotheses, evidence)

    assert result[0]["verification_status"] == "supported"
    assert any(
        "1800 ms" in item
        for item in result[0]["supporting_evidence"]
    )



def test_empty_hypotheses_return_empty_list():
    result = verify_hypotheses(
        [],
        {
            "logs": {"findings": []},
            "metrics": {"findings": []},
            "deployment": {"recent_deployment": False},
        },
    )

    assert result == []


def test_recent_deployment_alone_does_not_support_regression():
    hypotheses = [
        {
            "cause": "Deployment-related regression",
            "confidence": 0.70,
            "evidence": [
                "A recent deployment was reported.",
                "Current error rate is 25.0%.",
            ],
        }
    ]

    evidence = {
        "logs": {"findings": []},
        "metrics": {
            "findings": [
                {"metric": "error_rate", "value": 25.0}
            ]
        },
        "deployment": {
            "recent_deployment": True,
            "observation": (
                "A recent deployment was reported. "
                "Further evidence is needed to establish causation."
            ),
        },
    }

    result = verify_hypotheses(hypotheses, evidence)

    assert result[0]["verification_status"] == "inconclusive"
    assert any(
        "before and after" in item.lower()
        for item in result[0]["missing_evidence"]
    )
