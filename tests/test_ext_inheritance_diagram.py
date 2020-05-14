"""
    test_ext_inheritance_diagram
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Test sphinx.ext.inheritance_diagram extension.

    :copyright: Copyright 2007-2020 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import os
import sys
import collections

import pytest

from sphinx.ext.inheritance_diagram import (
    InheritanceDiagram, InheritanceGraph, InheritanceException, import_classes
)

CACHE = None


@pytest.fixture
def build_context(make_app, app_params, warning):
    """Build the whole sphinx rst for this extension a single time.

    It's a kind of module scope fixture but it uses function scope fixture.
    """
    global CACHE
    if CACHE is not None:
        return CACHE

    # monkey-patch InheritaceDiagram.run() and InheritanceGraph.generate_dot()
    # so we can get access to its results.
    orig_run = InheritanceDiagram.run
    orig_generate_dot = InheritanceGraph.generate_dot
    graphs = {}
    dots = {}

    def new_run(self):
        result = orig_run(self)
        node = result[0]
        source = os.path.basename(node.document.current_source).replace(".rst", "")
        graphs[source] = node['graph']
        node['graph']._source = source
        return result

    def new_generate_dot(self, *args, **kwargs):
        result = orig_generate_dot(self, *args, **kwargs)
        dots[self._source] = result
        return result

    InheritanceDiagram.run = new_run
    InheritanceGraph.generate_dot = new_generate_dot

    try:
        args, kwargs = app_params
        app = make_app(*args, **kwargs)
        app.builder.build_all()
    finally:
        InheritanceDiagram.run = orig_run
        InheritanceGraph.generate_dot = orig_generate_dot

    assert app.statuscode == 0

    html_warnings = warning.getvalue()
    assert html_warnings == ""
    
    results = {}
    Result = collections.namedtuple("Result", ["graph", "dot"])
    for k in graphs:
        r = Result(graphs[k], dots[k])
        results[k] = r

    CACHE = results
    return results


@pytest.mark.usefixtures('if_graphviz_found')
@pytest.mark.sphinx(buildername="html", testroot="inheritance")
def test_basic_diagram(status, build_context):
    """Basic inheritance diagram showing all classes"""
    for cls in build_context['basic_diagram'].graph.class_info:
        # use in b/c traversing order is different sometimes
        assert cls in [
            ('dummy.test.A', 'dummy.test.A', [], None),
            ('dummy.test.F', 'dummy.test.F', ['dummy.test.C'], None),
            ('dummy.test.C', 'dummy.test.C', ['dummy.test.A'], None),
            ('dummy.test.E', 'dummy.test.E', ['dummy.test.B'], None),
            ('dummy.test.D', 'dummy.test.D', ['dummy.test.B', 'dummy.test.C'], None),
            ('dummy.test.B', 'dummy.test.B', ['dummy.test.A'], None)
        ]

@pytest.mark.usefixtures('if_graphviz_found')
@pytest.mark.sphinx(buildername="html", testroot="inheritance")
def test_diagram_w_parts(status, build_context):
    """Inheritance diagram using :parts: 1 option"""
    for cls in build_context['diagram_w_parts'].graph.class_info:
        assert cls in [
            ('A', 'dummy.test.A', [], None),
            ('F', 'dummy.test.F', ['C'], None),
            ('C', 'dummy.test.C', ['A'], None),
            ('E', 'dummy.test.E', ['B'], None),
            ('D', 'dummy.test.D', ['B', 'C'], None),
            ('B', 'dummy.test.B', ['A'], None)
        ]


@pytest.mark.usefixtures('if_graphviz_found')
@pytest.mark.sphinx(buildername="html", testroot="inheritance")
def test_diagram_w_1_top_class(status, build_context):
    """Inheritance diagram with 1 top class"""
    # :top-classes: dummy.test.B
    # rendering should be
    #       A
    #        \
    #     B   C
    #    / \ / \
    #   E   D   F
    #
    for cls in build_context['diagram_w_1_top_class'].graph.class_info:
        assert cls in [
            ('dummy.test.A', 'dummy.test.A', [], None),
            ('dummy.test.F', 'dummy.test.F', ['dummy.test.C'], None),
            ('dummy.test.C', 'dummy.test.C', ['dummy.test.A'], None),
            ('dummy.test.E', 'dummy.test.E', ['dummy.test.B'], None),
            ('dummy.test.D', 'dummy.test.D', ['dummy.test.B', 'dummy.test.C'], None),
            ('dummy.test.B', 'dummy.test.B', [], None)
        ]


@pytest.mark.usefixtures('if_graphviz_found')
@pytest.mark.sphinx(buildername="html", testroot="inheritance")
def test_diagram_w_2_top_classes(status, build_context):
    """Inheritance diagram with 2 top classes"""
    # :top-classes: dummy.test.B, dummy.test.C
    # Note: we're specifying separate classes, not the entire module here
    # rendering should be
    #
    #     B   C
    #    / \ / \
    #   E   D   F
    #
    for cls in build_context['diagram_w_2_top_classes'].graph.class_info:
        assert cls in [
            ('dummy.test.F', 'dummy.test.F', ['dummy.test.C'], None),
            ('dummy.test.C', 'dummy.test.C', [], None),
            ('dummy.test.E', 'dummy.test.E', ['dummy.test.B'], None),
            ('dummy.test.D', 'dummy.test.D', ['dummy.test.B', 'dummy.test.C'], None),
            ('dummy.test.B', 'dummy.test.B', [], None)
        ]


@pytest.mark.usefixtures('if_graphviz_found')
@pytest.mark.sphinx(buildername="html", testroot="inheritance")
def test_diagram_module_w_2_top_classes(status, build_context):
    """Inheritance diagram with 2 top classes and specifying the entire
    module"""

    # rendering should be
    #
    #       A
    #     B   C
    #    / \ / \
    #   E   D   F
    #
    # Note: dummy.test.A is included in the graph before its descendants are even processed
    # b/c we've specified to load the entire module. The way InheritanceGraph works it is very
    # hard to exclude parent classes once after they have been included in the graph.
    # If you'd like to not show class A in the graph don't specify the entire module.
    # this is a known issue.
    for cls in build_context['diagram_module_w_2_top_classes'].graph.class_info:
        assert cls in [
            ('dummy.test.F', 'dummy.test.F', ['dummy.test.C'], None),
            ('dummy.test.C', 'dummy.test.C', [], None),
            ('dummy.test.E', 'dummy.test.E', ['dummy.test.B'], None),
            ('dummy.test.D', 'dummy.test.D', ['dummy.test.B', 'dummy.test.C'], None),
            ('dummy.test.B', 'dummy.test.B', [], None),
            ('dummy.test.A', 'dummy.test.A', [], None),
        ]


@pytest.mark.usefixtures('if_graphviz_found')
@pytest.mark.sphinx(buildername="html", testroot="inheritance")
def test_diagram_w_nested_classes(status, build_context):
    """Inheritance diagram involving a base class nested within another class
    """
    for cls in build_context['diagram_w_nested_classes'].graph.class_info:
        assert cls in [
            ('dummy.test_nested.A', 'dummy.test_nested.A', [], None),
            ('dummy.test_nested.C', 'dummy.test_nested.C', ['dummy.test_nested.A.B'], None),
            ('dummy.test_nested.A.B', 'dummy.test_nested.A.B', [], None)
        ]


@pytest.mark.usefixtures('if_graphviz_found')
@pytest.mark.sphinx(buildername="html", testroot="inheritance")
def test_diagram_w_uml(status, build_context):
    """Check that the empty arrow is part of the UML diagram
    """
    dot = build_context['diagram_w_uml'].dot
    assert 'arrowtail="empty"' in dot


@pytest.mark.sphinx('html', testroot='ext-inheritance_diagram')
@pytest.mark.usefixtures('if_graphviz_found')
def test_inheritance_diagram_png_html(app, status, warning):
    app.builder.build_all()

    content = (app.outdir / 'index.html').read_text()

    pattern = ('<div class="figure align-default" id="id1">\n'
               '<div class="graphviz">'
               '<img src="_images/inheritance-\\w+.png" alt="Inheritance diagram of test.Foo" '
               'class="inheritance graphviz" /></div>\n<p class="caption">'
               '<span class="caption-text">Test Foo!</span><a class="headerlink" href="#id1" '
               'title="Permalink to this image">\xb6</a></p>')
    assert re.search(pattern, content, re.M)


@pytest.mark.sphinx('html', testroot='ext-inheritance_diagram',
                    confoverrides={'graphviz_output_format': 'svg'})
@pytest.mark.usefixtures('if_graphviz_found')
def test_inheritance_diagram_svg_html(app, status, warning):
    app.builder.build_all()

    content = (app.outdir / 'index.html').read_text()

    pattern = ('<div class="figure align-default" id="id1">\n'
               '<div class="graphviz">'
               '<object data="_images/inheritance-\\w+.svg" '
               'type="image/svg\\+xml" class="inheritance graphviz">\n'
               '<p class=\"warning\">Inheritance diagram of test.Foo</p>'
               '</object></div>\n<p class="caption"><span class="caption-text">'
               'Test Foo!</span><a class="headerlink" href="#id1" '
               'title="Permalink to this image">\xb6</a></p>')
    assert re.search(pattern, content, re.M)


@pytest.mark.sphinx('latex', testroot='ext-inheritance_diagram')
@pytest.mark.usefixtures('if_graphviz_found')
def test_inheritance_diagram_latex(app, status, warning):
    app.builder.build_all()

    content = (app.outdir / 'python.tex').read_text()

    pattern = ('\\\\begin{figure}\\[htbp]\n\\\\centering\n\\\\capstart\n\n'
               '\\\\sphinxincludegraphics\\[\\]{inheritance-\\w+.pdf}\n'
               '\\\\caption{Test Foo!}\\\\label{\\\\detokenize{index:id1}}\\\\end{figure}')
    assert re.search(pattern, content, re.M)


@pytest.mark.sphinx('html', testroot='ext-inheritance_diagram',
                    srcdir='ext-inheritance_diagram-alias')
@pytest.mark.usefixtures('if_graphviz_found')
def test_inheritance_diagram_latex_alias(app, status, warning):
    app.config.inheritance_alias = {'test.Foo': 'alias.Foo'}
    app.builder.build_all()

    doc = app.env.get_and_resolve_doctree('index', app)
    aliased_graph = doc.children[0].children[3]['graph'].class_info
    assert len(aliased_graph) == 3
    assert ('test.Baz', 'test.Baz', ['test.Bar'], None) in aliased_graph
    assert ('test.Bar', 'test.Bar', ['alias.Foo'], None) in aliased_graph
    assert ('alias.Foo', 'alias.Foo', [], None) in aliased_graph

    content = (app.outdir / 'index.html').read_text()

    pattern = ('<div class="figure align-default" id="id1">\n'
               '<div class="graphviz">'
               '<img src="_images/inheritance-\\w+.png" alt="Inheritance diagram of test.Foo" '
               'class="inheritance graphviz" /></div>\n<p class="caption">'
               '<span class="caption-text">Test Foo!</span><a class="headerlink" href="#id1" '
               'title="Permalink to this image">\xb6</a></p>')
    assert re.search(pattern, content, re.M)


def test_import_classes(rootdir):
    from sphinx.parsers import Parser, RSTParser
    from sphinx.util.i18n import CatalogInfo

    try:
        sys.path.append(rootdir / 'test-ext-inheritance_diagram')
        from example.sphinx import DummyClass

        # got exception for unknown class or module
        with pytest.raises(InheritanceException):
            import_classes('unknown', None)
        with pytest.raises(InheritanceException):
            import_classes('unknown.Unknown', None)

        # got exception InheritanceException for wrong class or module
        # not AttributeError (refs: #4019)
        with pytest.raises(InheritanceException):
            import_classes('unknown', '.')
        with pytest.raises(InheritanceException):
            import_classes('unknown.Unknown', '.')
        with pytest.raises(InheritanceException):
            import_classes('.', None)

        # a module having no classes
        classes = import_classes('sphinx', None)
        assert classes == []

        classes = import_classes('sphinx', 'foo')
        assert classes == []

        # all of classes in the module
        classes = import_classes('sphinx.parsers', None)
        assert set(classes) == {Parser, RSTParser}

        # specified class in the module
        classes = import_classes('sphinx.parsers.Parser', None)
        assert classes == [Parser]

        # specified class in current module
        classes = import_classes('Parser', 'sphinx.parsers')
        assert classes == [Parser]

        # relative module name to current module
        classes = import_classes('i18n.CatalogInfo', 'sphinx.util')
        assert classes == [CatalogInfo]

        # got exception for functions
        with pytest.raises(InheritanceException):
            import_classes('encode_uri', 'sphinx.util')

        # import submodule on current module (refs: #3164)
        classes = import_classes('sphinx', 'example')
        assert classes == [DummyClass]
    finally:
        sys.path.pop()
