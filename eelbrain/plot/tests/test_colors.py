# Author: Christian Brodbeck <christianbrodbeck@nyu.edu>
from nose.tools import eq_, assert_in, assert_raises, assert_greater

from eelbrain import datasets, plot


def test_generate_colors():
    "Test functions for assigning colors to cells"
    ds = datasets.get_uv()
    cells_1 = ('A', 'B')
    cells_2 = ('a', 'b', 'c')

    colors = plot.colors_for_oneway(cells_1)
    eq_(len(colors), len(cells_1))

    colors = plot.colors_for_twoway(cells_1, cells_2)
    eq_(len(colors), len(cells_1) * len(cells_2))

    colors = plot.colors_for_twoway(cells_2, cells_1)
    eq_(len(colors), len(cells_1) * len(cells_2))

    # colors_for_categorial()
    f = ds['A']
    colors = plot.colors_for_categorial(f)
    for cell in f.cells:
        assert_in(cell, colors)

    i = ds.eval("A%B")
    colors = plot.colors_for_categorial(i)
    for cell in i.cells:
        assert_in(cell, colors)

    i = ds.eval("A%B%rm")
    colors = plot.colors_for_categorial(i)
    for cell in i.cells:
        assert_in(cell, colors)

    assert_raises(TypeError, plot.colors_for_categorial, "A%B")


def test_plot_colorbar():
    "Test plot.ColorBar()"
    p = plot.ColorBar('jet', -1, 1, show=False)
    p.close()
    p = plot.ColorBar('jet', -1, 1, orientation='vertical', show=False)
    p.close()
    p = plot.ColorBar('jet', -1, 1, label_position='top', show=False)
    p.close()
    p = plot.ColorBar('jet', -1, 1, orientation='vertical',
                      label_position='right', show=False)
    p.close()


def test_plot_colors():
    "Test plotting color schemes"
    cells_1 = ('A', 'B')
    cells_2 = ('a', 'b', 'c')

    colors = plot.colors_for_oneway(cells_1)
    p = plot.ColorList(colors, show=False)
    w0, h0 = p.figure.get_size_inches()
    p.close()

    p = plot.ColorList(colors, labels={'A': 'A'*20, 'B': 'Bbb'}, show=False)
    w, h = p.figure.get_size_inches()
    eq_(h, h0)
    assert_greater(w, w0)
    p.close()

    colors = plot.colors_for_twoway(cells_1, cells_2)
    p = plot.ColorList(colors, show=False)
    p.close()
