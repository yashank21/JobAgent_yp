import pytest

from app.collectors.base import BaseCollector


def test_base_collector_cannot_be_instantiated():

    with pytest.raises(TypeError):
        BaseCollector()