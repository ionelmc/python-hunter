import os

os.environ['PUREPYTHONHUNTER'] = 'yes'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.autosummary',
    'sphinx.ext.coverage',
    'sphinx.ext.doctest',
    'sphinx.ext.extlinks',
    'sphinx.ext.ifconfig',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
]
source_suffix = '.rst'
master_doc = 'index'
project = 'Hunter'
year = '2015-2025'
author = 'Ionel Cristian Mărieș'
copyright = f'{year}, {author}'
try:
    from importlib import metadata

    version = release = metadata.version('hunter')
except Exception:
    import traceback

    traceback.print_exc()
    version = release = '3.8.0'

pygments_style = 'trac'
templates_path = ['.']
extlinks = {
    'issue': ('https://github.com/ionelmc/python-hunter/issues/%s', '#%s'),
    'pr': ('https://github.com/ionelmc/python-hunter/pull/%s', 'PR #%s'),
}

html_theme = 'furo'
html_theme_options = {
    'githuburl': 'https://github.com/ionelmc/python-hunter/',
}

html_use_smartypants = True
html_last_updated_fmt = '%b %d, %Y'
html_split_index = False
html_short_title = f'{project}-{version}'

napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = False
