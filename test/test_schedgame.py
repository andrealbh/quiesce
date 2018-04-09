import pytest
import numpy as np
from gameanalysis import gamegen
from gameanalysis import utils

from egta import gamesched
from egta import schedgame


sizes = [
    ([3], [3]),
    ([3, 2], [2, 3]),
    ([2, 2, 2], [2, 2, 2]),
]


@pytest.mark.asyncio
@pytest.mark.parametrize('players,strats', sizes)
@pytest.mark.parametrize('_', range(20))
async def test_random_caching(players, strats, _):
    game = gamegen.samplegame(players, strats)
    rest1, rest2 = game.random_restrictions(2)
    mixes = np.random.random((2, game.num_strats))
    mixes *= [rest1, rest2]
    mixes /= np.add.reduceat(mixes, game.role_starts, 1).repeat(
        game.num_role_strats, 1)
    mix1, mix2 = mixes
    sched = gamesched.samplegamesched(game)
    sgame = schedgame.schedgame(sched)
    assert str(sgame) == str(sched)

    rgame11 = await sgame.get_restricted_game(rest1)
    rgame21 = await sgame.get_restricted_game(rest2)
    devs11 = await sgame.get_deviation_game(rest1)
    devs21 = await sgame.get_deviation_game(rest2)

    rgame12 = await sgame.get_restricted_game(rest1)
    rgame22 = await sgame.get_restricted_game(rest2)
    assert rgame11 == rgame12
    assert rgame21 == rgame22

    devs12 = await sgame.get_deviation_game(rest1)
    devs22 = await sgame.get_deviation_game(rest2)
    assert devs11 == devs12
    assert devs21 == devs22


@pytest.mark.asyncio
@pytest.mark.parametrize('players,strats', sizes)
@pytest.mark.parametrize('_', range(20))
async def test_random_redgame(players, strats, _):
    game = gamegen.samplegame(players, strats)
    rest = game.random_restriction()
    sched = gamesched.samplegamesched(game)
    sgame = schedgame.schedgame(sched)

    devgame1 = await sgame.get_deviation_game(rest)
    prof = devgame1.profiles()[np.all(
        (devgame1.profiles() == 0) | ~np.isnan(devgame1.payoffs()),
        1).nonzero()[0][0]]
    assert prof in devgame1
    assert (devgame1.num_complete_profiles <= devgame1.num_profiles <=
            devgame1.num_all_profiles)

    devgame2 = await sgame.get_deviation_game(rest)
    assert hash(devgame1) == hash(devgame2)
    assert devgame1 == devgame2
    assert devgame1 + devgame2 == devgame2 + devgame1
    assert np.allclose(devgame1.get_payoffs(prof),
                       devgame2.get_payoffs(prof))

    rrest = devgame1.random_restriction()
    assert devgame1.restrict(rrest) == devgame2.restrict(rrest)


@pytest.mark.asyncio
@pytest.mark.parametrize('players,strats', sizes)
@pytest.mark.parametrize('_', range(20))
async def test_random_complete_dev(players, strats, _):
    game = gamegen.samplegame(players, strats)
    sched = gamesched.SampleGameScheduler(game)
    sgame = schedgame.schedgame(sched)
    mix = sgame.random_sparse_mixture()
    supp = mix > 0
    dev_game = await sgame.get_deviation_game(supp)
    devs, jac = dev_game.deviation_payoffs(mix, jacobian=True)
    assert not np.isnan(devs).any()
    assert not np.isnan(jac[supp]).any()
    assert np.isnan(jac[~supp]).all()
    for r in range(sgame.num_roles):
        mask = r == sgame.role_indices
        dev_game = await sgame.get_deviation_game(supp, role_index=r)
        rdevs = dev_game.deviation_payoffs(mix)
        assert np.allclose(rdevs[supp], devs[supp])
        assert np.allclose(rdevs[mask], devs[mask])
        assert supp[~mask].all() or np.isnan(rdevs[~mask]).any()


@pytest.mark.asyncio
@pytest.mark.parametrize('players,strats', sizes)
@pytest.mark.parametrize('_', range(20))
async def test_random_normalize(players, strats, _):
    game = gamegen.samplegame(players, strats)
    sched = gamesched.SampleGameScheduler(game)
    sgame = schedgame.schedgame(sched)
    rgame = await sgame.get_restricted_game(np.ones(game.num_strats, bool))
    ngame = rgame.normalize()
    assert np.all(ngame.payoffs() >= -1e-7)
    assert np.all(ngame.payoffs() <= 1 + 1e-7)
