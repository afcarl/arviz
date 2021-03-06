import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import gaussian, convolve
from scipy.stats import entropy


def kdeplot(values, label=None, shade=0, color_shade=None, bw=4.5, rotated=False,
            ax=None, kwargs_shade=None, **kwargs):
    """
    1D KDE plot taking into account boundary conditions

    Parameters
    ----------
    values : array-like
        Values to plot
    label : string
        Text to include as part of the legend
    shade : float
        Alpha blending value for the shaded area under the curve, between 0
        (no shade) and 1 (opaque). Defaults to 0
    color_shade : valid matplotlib color
        Color used for the shaed are under the curve. Defaults to None
    bw : float
        Bandwidth scaling factor. Should be larger than 0. The higher this number the smoother the
        KDE will be. Defaults to 4.5 which is essentially the same as the Scott's rule of thumb
        (the default rule used by SciPy).
    ax : matplotlib axes
    kwargs_shade : dicts, optional
        Additional keywords passed to `matplotlib.axes.Axes.fill_between`
        (to control the shade)
    Returns
    ----------
    ax : matplotlib axes

    """
    if ax is None:
        _, ax = plt.subplots()

    if kwargs_shade is None:
        kwargs_shade = {}

    density, l, u = fast_kde(values, bw)
    x = np.linspace(l, u, len(density))
    if rotated:
        x, density = density, x

    ax.plot(x, density, label=label, **kwargs)
    if shade:
        ax.fill_between(x, density, alpha=shade, color=color_shade, **kwargs_shade)

    if rotated:
        ax.set_xlim(0, auto=True)
    else:
        ax.set_ylim(0, auto=True)

    return ax


def fast_kde(x, bw=4.5):
    """
    A fft-based Gaussian kernel density estimate (KDE)
    The code was adapted from https://github.com/mfouesneau/faststats

    Parameters
    ----------
    x : Numpy array or list
    bw : float
        Bandwidth scaling factor for the KDE. Should be larger than 0. The higher this number the
        smoother the KDE will be. Defaults to 4.5 which is essentially the same as the Scott's rule
        of thumb (the default rule used by SciPy).

    Returns
    -------
    density: A gridded 1D KDE of the input points (x)
    xmin: minimum value of x
    xmax: maximum value of x
    """
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    nx = 200

    xmin, xmax = np.min(x), np.max(x)

    dx = (xmax - xmin) / (nx - 1)
    std_x = entropy(x - xmin) * bw
    if ~np.isfinite(std_x):
        std_x = 0.
    grid, _ = np.histogram(x, bins=nx)

    scotts_factor = n ** (-0.2)
    kern_nx = int(scotts_factor * 2 * np.pi * std_x)
    kernel = gaussian(kern_nx, scotts_factor * std_x)

    npad = min(nx, 2 * kern_nx)
    grid = np.concatenate([grid[npad: 0: -1], grid, grid[nx: nx - npad: -1]])
    density = convolve(grid, kernel, mode='same')[npad: npad + nx]

    norm_factor = n * dx * (2 * np.pi * std_x ** 2 * scotts_factor ** 2) ** 0.5

    density = density / norm_factor

    return density, xmin, xmax
