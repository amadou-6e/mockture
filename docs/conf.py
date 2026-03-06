import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "mockture"
author = "Mockture Contributors"
release = "0.1.0"

# -- Extensions ---------------------------------------------------------------
# autodoc   : generate API reference from docstrings
# napoleon  : parse Google-style docstrings
# intersphinx : link to stdlib and pytest docs from the API reference
# viewcode  : "view source" links on API pages

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pytest": ("https://docs.pytest.org/en/stable/", None),
}

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}

napoleon_google_docstring = True
napoleon_numpy_docstring = False

# -- Build --------------------------------------------------------------------
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- HTML output --------------------------------------------------------------
# furo: minimal, dark-mode-ready, no JS framework dependency.
# Current community standard for new Python developer libraries (2024-2025).
# Add to dev dependencies: pip install furo
html_theme = "furo"
html_title = "mockture"

