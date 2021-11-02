import pytest

a = [(1,1), (2,1), (3,3) ]

@pytest.mark.parametrize('arg', a)
def test_(arg):
    assert arg[0] == arg[1]

