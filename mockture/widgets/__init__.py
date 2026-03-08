"""Optional Jupyter widgets for mockture.

Install the extra dependency before importing::

    pip install 'mockture[widgets]'

Usage::

    from mockture.widgets import FlowComposer

    composer = FlowComposer(
        templates_path="configs/api.templates.yml",
        flows_path="configs/api.flows.yml",
    )
    composer.show()
"""

from mockture.widgets.composer import FlowComposer
from mockture.widgets.mermaid import flow_to_mermaid, mermaid_html

__all__ = ["FlowComposer", "flow_to_mermaid", "mermaid_html"]
