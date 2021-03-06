# Author: Christian Brodbeck <christianbrodbeck@nyu.edu>
import numpy as np

from . import fmtxt
from . import plot
from . import test
from ._data_obj import cellname, combine
from ._stats.stats import ttest_t
from .fmtxt import ms, Section, Figure, linebreak


def n_of(n, of, plural_for_0=False):
    "n_of(3, 'epoch') -> '3 epochs'"
    if n == 0:
        return "no " + plural(of, not plural_for_0)
    return str(n) + ' ' + plural(of, n)


def plural(noun, n):
    "plural('house', 2) -> 'houses'"
    if n == 1:
        return noun
    else:
        return noun + 's'


def enumeration(items, link='and'):
    "['a', 'b', 'c'] -> 'a, b and c'"
    items = tuple(map(str, items))
    if len(items) >= 2:
        return (' %s ' % link).join((', '.join(items[:-1]), items[-1]))
    elif len(items) == 1:
        return items[0]
    else:
        raise ValueError("items=%s" % repr(items))


def named_list(items, name='item'):
    "named_list([1, 2, 3], 'number') -> 'numbers (1, 2, 3)"
    if len(items) == 1:
        return "%s (%r)" % (name, items[0])
    else:
        if name.endswith('y'):
            name = name[:-1] + 'ie'
        return "%ss (%s)" % (name, ', '.join(map(repr, items)))


def format_samples(res):
    if res.samples == -1:
        return "a complete set of %i permutations" % res.n_samples
    elif res.samples is None:
        return "no permutations"
    else:
        return "%i random permutations" % res.n_samples


def format_timewindow(res):
    "Format a description of the time window for a test result"
    uts = res._time_dim
    return '%s - %s ms' % (tstart(res.tstart, uts), tstop(res.tstop, uts))


def tstart(tstart, uts):
    if tstart is None:
        return ms(uts.tmin)
    else:
        return ms(tstart)


def tstop(tstop, uts):
    if tstop is None:
        return ms(uts.tmax + uts.tstep)
    else:
        return ms(tstop)


def sensor_results(res, ds, color):
    report = Section("Results")
    if res._kind == 'cluster':
        p = plot.Topomap(res, show=False)
        report.add_figure("Significant clusters.", p)
        p.close()

        report.add_figure("All clusters.", res.clusters)
    else:
        raise NotImplementedError("Result kind %r" % res._kind)
    return report


def sensor_time_results(res, ds, colors, include=1):
    y = ds.eval(res.Y)
    if res._kind in ('raw', 'tfce'):
        report = Section("Results")
        section = report.add_section("P<=.05")
        sensor_bin_table(section, res, 0.05)
        clusters = res.find_clusters(0.05, maps=True)
        clusters.sort('tstart')
        for cluster in clusters.itercases():
            sensor_time_cluster(section, cluster, y, res._plot_model(), ds,
                                colors, res.match)

        # trend section
        section = report.add_section("Trend: p<=.1")
        sensor_bin_table(section, res, 0.1)

        # not quite there section
        section = report.add_section("Anything: P<=.2")
        sensor_bin_table(section, res, 0.2)
    elif res._kind == 'cluster':
        report = Section("Clusters")
        sensor_bin_table(report, res)
        clusters = res.find_clusters(include, maps=True)
        clusters.sort('tstart')
        for cluster in clusters.itercases():
            sensor_time_cluster(report, cluster, y, res._plot_model(), ds,
                                colors, res.match)
    else:
        raise NotImplementedError("Result kind %r" % res._kind)
    return report


def sensor_bin_table(section, res, pmin=1):
    if pmin == 1:
        caption = "All clusters"
    else:
        caption = "p <= %.s" % pmin

    for effect, cdist in res._iter_cdists():
        ndvar = cdist.masked_parameter_map(pmin)
        if not ndvar.any():
            if effect:
                text = '%s: nothing\n' % effect
            else:
                text = 'Nothing\n'
            section.add_paragraph(text)
            continue
        elif effect:
            caption_ = "%s: %s" % (effect, caption)
        else:
            caption_ = caption
        p = plot.TopomapBins(ndvar, show=False)
        section.add_image_figure(p, caption_)


def sensor_time_cluster(section, cluster, y, model, ds, colors, match='subject'):
    # cluster properties
    tstart_ms = ms(cluster['tstart'])
    tstop_ms = ms(cluster['tstop'])

    # section/title
    title = ("{tstart}-{tstop} p={p}{mark} {effect}"
             .format(tstart=tstart_ms, tstop=tstop_ms,
                     p='%.3f' % cluster['p'],
                     effect=cluster.get('effect', ''),
                     location=cluster.get('location', ''),
                     mark=cluster['sig']).strip())
    while '  ' in title:
        title = title.replace('  ', ' ')
    section = section.add_section(title)

    # description
    paragraph = section.add_paragraph("Id %i" % cluster['id'])
    if 'v' in cluster:
        paragraph.append(", v=%s" % cluster['v'])

    # add cluster image to report
    topo = y.summary(time=(cluster['tstart'], cluster['tstop']))
    cluster_topo = cluster['cluster'].any('time')
    cluster_topo.info['contours'] = {0.5: (1, 1, 0)}
    if model:
        x = ds.eval(model)
        topos = [[topo[x == cell].summary('case', name=cellname(cell)),
                  cluster_topo] for cell in x.cells]
    else:
        topos = [[topo, cluster_topo]]
    p = plot.Topomap(topos, axh=3, nrow=1, show=False)
    p.mark_sensors(np.flatnonzero(cluster_topo.x), c='y', marker='o')

    caption_ = ["Cluster"]
    if 'effect' in cluster:
        caption_.extend(('effect of', cluster['effect']))
    caption_.append("%i - %i ms." % (tstart_ms, tstop_ms))
    caption = ' '.join(caption_)
    section.add_image_figure(p, caption)
    p.close()

    cluster_timecourse(section, cluster, y, 'sensor', model, ds, colors, match)


def source_results(res, surfer_kwargs={}, title="Results", diff_cmap=None,
                   table_pmax=0.2, plot_pmax=0.05):
    "Only used for TRF-report"
    sec = Section(title)

    # raw difference
    brain = plot.brain.surfer_brain(res.difference, diff_cmap, **surfer_kwargs)
    cbar = brain.plot_colorbar(orientation='vertical', show=False)
    sec.add_figure("Correlation increase.", (brain.image('correlation'), cbar))
    brain.close()
    cbar.close()

    # test of difference
    if res._kind == 'cluster':
        clusters = res.find_clusters(table_pmax)
        pmax_repr = str(table_pmax)[1:]
        ctable = clusters.as_table(midrule=True, count=True, caption="All "
                                   "clusters with p<=%s." % pmax_repr)
        sec.append(ctable)

        clusters = res.find_clusters(plot_pmax, True)
        for cluster in clusters.itercases():
            # only plot relevant hemisphere
            sec.add_figure("Cluster %i: p=%.3f" % (cluster['id'], cluster['p']),
                           source_cluster_im(cluster['cluster'], surfer_kwargs),
                           {'class': 'float'})
        sec.append(linebreak)
    return sec


def source_cluster_im(ndvar, surfer_kwargs, mark_sources=None):
    """Plot ('source',) NDVar, only plot relevant hemi

    Parameters
    ----------
    ndvar : NDVar (source,)
        Source space data.
    surfer_kwargs : dict
        Keyword arguments for PySurfer plot.
    mark_sources : SourceSpace index
        Sources to mark on the brain plot (as SourceSpace index).
    """
    kwargs = surfer_kwargs.copy()
    if not ndvar.sub(source='lh').any():
        kwargs['hemi'] = 'rh'
    elif not ndvar.sub(source='rh').any():
        kwargs['hemi'] = 'lh'
    if ndvar.x.dtype.kind == 'b':
        brain = plot.brain.dspm(ndvar, 0, 1.5, **kwargs)
    elif ndvar.x.dtype.kind == 'i':  # map of cluster ids
        brain = plot.brain.surfer_brain(ndvar, 'jet', **kwargs)
    else:
        brain = plot.brain.cluster(ndvar, **kwargs)

    # mark sources on the brain
    if mark_sources is not None:
        mark_sources = np.atleast_1d(ndvar.source._array_index(mark_sources))
        i_hemi_split = np.searchsorted(mark_sources, ndvar.source.lh_n)
        lh_indexes = mark_sources[:i_hemi_split]
        if lh_indexes:
            lh_vertices = ndvar.source.lh_vertices[lh_indexes]
            brain.add_foci(lh_vertices, True, hemi='lh', color="gold")
        rh_indexes = mark_sources[i_hemi_split:]
        if rh_indexes:
            rh_vertices = ndvar.source.rh_vertices[rh_indexes - ndvar.source.lh_n]
            brain.add_foci(rh_vertices, True, hemi='rh', color="gold")

    out = brain.image(ndvar.name)
    brain.close()
    return out


def source_time_results(res, ds, colors, include=0.1, surfer_kwargs={},
                        title="Results", parc=True):
    report = Section(title)
    y = ds[res.Y]
    if parc is True:
        parc = res._first_cdist.parc
    model = res._plot_model()
    if parc and res._kind == 'cluster':
        source_bin_table(report, res, surfer_kwargs)

        # add subsections for individual labels
        title = "{tstart}-{tstop} p={p}{mark} {effect}"
        for label in y.source.parc.cells:
            section = report.add_section(label.capitalize())

            clusters = res.find_clusters(source=label)
            source_time_clusters(section, clusters, y, ds, model, include,
                                 title, colors, res)
    elif not parc and res._kind == 'cluster':
        source_bin_table(report, res, surfer_kwargs)

        clusters = res.find_clusters()
        clusters.sort('tstart')
        title = "{tstart}-{tstop} {location} p={p}{mark} {effect}"
        source_time_clusters(report, clusters, y, ds, model, include, title,
                             colors, res)
    elif not parc and res._kind in ('raw', 'tfce'):
        section = report.add_section("P<=.05")
        source_bin_table(section, res, surfer_kwargs, 0.05)
        clusters = res.find_clusters(0.05, maps=True)
        clusters.sort('tstart')
        title = "{tstart}-{tstop} {location} p={p}{mark} {effect}"
        for cluster in clusters.itercases():
            source_time_cluster(section, cluster, y, model, ds, title, colors,
                                res.match)

        # trend section
        section = report.add_section("Trend: p<=.1")
        source_bin_table(section, res, surfer_kwargs, 0.1)

        # not quite there section
        section = report.add_section("Anything: P<=.2")
        source_bin_table(section, res, surfer_kwargs, 0.2)
    elif parc and res._kind in ('raw', 'tfce'):
        title = "{tstart}-{tstop} p={p}{mark} {effect}"
        for label in y.source.parc.cells:
            section = report.add_section(label.capitalize())
            # TODO:  **sub is not implemented in find_clusters()
            clusters_sig = res.find_clusters(0.05, True, source=label)
            clusters_trend = res.find_clusters(0.1, True, source=label)
            clusters_trend = clusters_trend.sub("p>0.05")
            clusters_all = res.find_clusters(0.2, True, source=label)
            clusters_all = clusters_all.sub("p>0.1")
            clusters = combine((clusters_sig, clusters_trend, clusters_all))
            clusters.sort('tstart')
            source_time_clusters(section, clusters, y, ds, model, include,
                                 title, colors, res)
    else:
        raise RuntimeError
    return report


def source_bin_table(section, res, surfer_kwargs, pmin=1):
    caption = ("All clusters in time bins. Each plot shows all sources "
               "that are part of a cluster at any time during the "
               "relevant time bin. Only the general minimum duration and "
               "source number criterion are applied.")

    for effect, cdist in res._iter_cdists():
        ndvar = cdist.masked_parameter_map(pmin)
        if not ndvar.any():
            if effect:
                text = '%s: nothing\n' % effect
            else:
                text = 'Nothing\n'
            section.add_paragraph(text)
            continue
        elif effect:
            caption_ = "%s: %s" % (effect, caption)
        else:
            caption_ = caption
        im = plot.brain.bin_table(ndvar, **surfer_kwargs)
        section.add_image_figure(im, caption_)


def source_time_lm(lm, pmin):
    if pmin == 0.1:
        ps = (0.1, 0.01, 0.05)
    elif pmin == 0.05:
        ps = (0.05, 0.001, 0.01)
    elif pmin == 0.01:
        ps = (0.01, 0.0001, 0.001)
    elif pmin == 0.001:
        ps = (0.001, 0.00001, 0.0001)
    else:
        raise ValueError("pmin=%s" % pmin)
    out = Section("SPMs")
    ts = [ttest_t(p, lm.df) for p in ps]
    for term in lm.column_names:
        im = plot.brain.dspm_bin_table(lm.t(term), *ts, summary='extrema')
        out.add_section(term, im)
    return out


def source_time_clusters(section, clusters, y, ds, model, include, title, colors, res):
    """Plot cluster with source and time dimensions

    Parameters
    ----------
    ...
    legend : None | fmtxt.Image
        Legend (if shared with other figures).

    Returns
    -------
    legend : fmtxt.Image
        Legend to share with other figures.
    """
    # compute clusters
    if clusters.n_cases == 0:
        section.append("No clusters found.")
        return

    section.append(
        clusters.as_table(midrule=True, count=True, caption="All clusters."))

    # plot individual clusters
    clusters = clusters.sub("p < %s" % include)
    # in non-threshold based tests, clusters don't have unique IDs
    add_cluster_im = 'cluster' not in clusters
    is_multi_effect_result = 'effect' in clusters
    for cluster in clusters.itercases():
        if add_cluster_im:
            if is_multi_effect_result:
                cluster['cluster'] = res.cluster(cluster['id'], cluster['effect'])
            else:
                cluster['cluster'] = res.cluster(cluster['id'])
        source_time_cluster(section, cluster, y, model, ds, title, colors,
                            res.match)


def source_time_cluster(section, cluster, y, model, ds, title, colors, match):
    # cluster properties
    tstart_ms = ms(cluster['tstart'])
    tstop_ms = ms(cluster['tstop'])
    effect = cluster.get('effect', '')

    # section/title
    if title is not None:
        title_ = title.format(tstart=tstart_ms, tstop=tstop_ms,
                              p='%.3f' % cluster['p'], effect=effect,
                              location=cluster.get('location', ''),
                              mark=cluster['sig']).strip()
        while '  ' in title_:
            title_ = title_.replace('  ', ' ')
        section = section.add_section(title_)

    # description
    txt = section.add_paragraph("Id %i" % cluster['id'])
    if 'v' in cluster:
        txt.append(", v=%s" % cluster['v'])
    if 'p_parc' in cluster:
        txt.append(", corrected across all ROIs: ")
        txt.append(fmtxt.eq('p', cluster['p_parc'], 'mcc', '%s', drop0=True))
    txt.append('.')

    # add cluster image to report
    brain = plot.brain.cluster(cluster['cluster'].sum('time'), surf='inflated')
    cbar = brain.plot_colorbar(orientation='vertical', show=False)
    caption = "Cluster"
    if effect:
        caption += 'effect of ' + effect
    caption += "%i - %i ms." % (tstart_ms, tstop_ms)
    section.add_figure(caption, (brain.image('cluster_spatial'), cbar))
    brain.close()
    cbar.close()
    # add cluster time course
    if effect:
        reduced_model = '%'.join(effect.split(' x '))
        if len(reduced_model) < len(model):
            colors_ = plot.colors_for_categorial(ds.eval(reduced_model))
            cluster_timecourse(section, cluster, y, 'source', reduced_model, ds,
                               colors_, match)
    cluster_timecourse(section, cluster, y, 'source', model, ds, colors, match)


def cluster_timecourse(section, cluster, y, dim, model, ds, colors, match):
    c_extent = cluster['cluster']
    cid = cluster['id']

    # cluster time course
    idx = c_extent.any('time')
    tc = y[idx].mean(dim)
    p = plot.UTSStat(tc, model, match=match, ds=ds, legend=None, h=4,
                     colors=colors, show=False)
    # mark original cluster
    for ax in p._axes:
        ax.axvspan(cluster['tstart'], cluster['tstop'], color='r',
                   alpha=0.2, zorder=-2)

    if model:
        # legend
        legend_p = p.plot_legend(show=False)
        legend = legend_p.image("Legend")
        legend_p.close()
    else:
        p._axes[0].axhline(0, color='k')
    image_tc = p.image('cluster_%i_timecourse' % cid)
    p.close()

    # Barplot
    idx = (c_extent != 0)
    v = y.mean(idx)
    p = plot.Barplot(v, model, match, ds=ds, corr=None, colors=colors, h=4,
                     show=False)
    image_bar = p.image('cluster_%i_barplot.png' % cid)
    p.close()

    # Boxplot
    p = plot.Boxplot(v, model, match, ds=ds, corr=None, colors=colors, h=4,
                     show=False)
    image_box = p.image('cluster_%i_boxplot.png' % cid)
    p.close()

    if model:
        # compose figure
        section.add_figure("Time course in cluster area, and average value in "
                           "cluster by condition, with pairwise t-tests.",
                           [image_tc, image_bar, image_box, legend])
        # pairwise test table
        res = test.pairwise(v, model, match, ds=ds, corr=None)
        section.add_figure("Pairwise t-tests of average value in cluster by "
                           "condition", res)
    else:
        section.add_figure("Time course in cluster area, and average value in "
                           "cluster.", [image_tc, image_bar, image_box])


def roi_timecourse(doc, ds, label, res, colors, merged_dist=None):
    "Plot ROI time course with cluster permutation test"
    label_name = label[:-3].capitalize()
    hemi = label[-2].capitalize()
    title = ' '.join((label_name, hemi))
    caption = "Source estimates in %s (%s)." % (label_name, hemi)
    doc.append(time_results(res, ds, colors, title, caption, merged_dist=merged_dist))


def time_results(res, ds, colors, title='Results', caption="Timecourse",
                 pairwise_pmax=0.1, merged_dist=None):
    """Add time course with clusters

    Parameters
    ----------
    res : Result
        Result of the temporal cluster test.
    ds : Dataset
        Data.
    colors : dict
        Cell colors.
    title : str
        Section title.
    merged_dist : MergedTemporalClusterDist
        Merged cluster distribution for correcting p values across ROIs
    """
    if merged_dist:
        clusters = merged_dist.correct_cluster_p(res)
    else:
        clusters = res.find_clusters()
    if clusters.n_cases:
        idx = clusters.eval("p.argmin()")
        max_sig = clusters['sig'][idx]
        if max_sig:
            title += max_sig
    section = Section(title)

    # compose captions
    if clusters.n_cases:
        c_caption = ("Clusters in time window %s based on %s."
                     % (format_timewindow(res), format_samples(res)))
        tc_caption = caption
    else:
        c_caption = "No clusters found %s." % format_timewindow(res)
        tc_caption = ' '.join((caption, c_caption))

    # plotting arguments
    model = res._plot_model()
    sub = res._plot_sub()

    # add UTSStat plot
    p = plot.UTSStat(res.Y, model, None, res.match, sub, ds, colors=colors,
                     legend=None, clusters=clusters, show=False)
    ax = p._axes[0]
    if res.tstart is not None:
        ax.axvline(res.tstart, color='k')
    if res.tstop is not None:
        ax.axvline(res.tstop, color='k')
    image = p.image('%s_cluster.png')
    legend_p = p.plot_legend(show=False)
    legend = legend_p.image("Legend")
    section.add_figure(tc_caption, [image, legend])
    p.close()
    legend_p.close()

    # add cluster table
    if clusters.n_cases:
        t = clusters.as_table(midrule=True, caption=c_caption)
        section.append(t)

    # pairwise plots
    model_ = model
    colors_ = colors
    if pairwise_pmax is not None:
        plots = []
        clusters_ = clusters.sub("p <= %s" % pairwise_pmax)
        clusters_.sort("tstart")
        for cluster in clusters_.itercases():
            cid = cluster['id']
            c_tstart = cluster['tstart']
            c_tstop = cluster['tstop']
            tw_str = "%s - %s ms" % (ms(c_tstart), ms(c_tstop))
            if 'effect' in cluster:
                title = "%s %s%s: %s" % (cluster['effect'], cid, cluster['sig'], tw_str)
                model_ = cluster['effect'].replace(' x ', '%')
                colors_ = colors if model_ == model else None
            else:
                title = "Cluster %s%s: %s" % (cid, cluster['sig'], tw_str)
            y_ = ds[res.Y].summary(time=(c_tstart, c_tstop))
            p = plot.Barplot(y_, model_, res.match, sub, ds=ds, corr=None,
                             show=False, colors=colors_, title=title)
            plots.append(p.image())
            p.close()

        section.add_image_figure(plots, "Value in the time-window of the clusters "
                                 "with uncorrected pairwise t-tests.")

    return section


def result_report(res, ds, title=None, colors=None):
    """Automatically generate section from testnd Result

    Parameters
    ----------
    res : Result
        Test-result.
    ds : Dataset
        Dataset containing the data on which the test was performed.
    """
    sec = Section(title or res._name())

    dims = {dim.name for dim in res._dims}
    sec.append(res.info_list())

    if dims == {'time'}:
        sec.append(time_results(res, ds, colors))
    elif dims == {'sensor'}:
        sec.append(sensor_results(res, ds, colors))
    elif dims == {'time', 'sensor'}:
        sec.append(sensor_time_results(res, ds, colors))
    elif dims == {'time', 'source'}:
        sec.append(source_time_results(res, ds, colors))
    else:
        raise NotImplementedError("dims=%r" % dims)
    return sec
