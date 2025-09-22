"""Basic 503 retry test"""

from unittest.mock import patch, Mock
from gql.transport.exceptions import TransportServerError
from bal_tools.subgraph import Subgraph


def test_503_retry():
    """Test 503 retry recovers after failures"""
    subgraph = Subgraph("mainnet")

    with patch("bal_tools.subgraph.RequestsHTTPTransport"):
        with patch("bal_tools.subgraph.Client") as mock_client:
            with patch("time.sleep"):
                mock_instance = Mock()
                mock_client.return_value = mock_instance

                # fail twice with 503, then succeed
                mock_instance.execute.side_effect = [
                    TransportServerError("503"),
                    TransportServerError("503"),
                    {"data": "ok"},
                ]

                result = subgraph.fetch_graphql_data("core", "{ test }", {})
                assert result == {"data": "ok"}
