from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Image

from testplan.common.exporters.pdf import RowStyle, create_table
from testplan.common.exporters.pdf import format_table_style
from testplan.common.utils.registry import Registry
from testplan.testing.multitest.entries import base

from .. import constants
from ..base import BaseRowRenderer, RowData


class SerializedEntryRegistry(Registry):
    """
        Registry that is used for binding assertion classes to PDF renderers.

        Keep in mind that we pass around serialized version of assertion objects
        (generated via `multitest.entries.schemas`) meaning that lookup
        arguments will be dictionary representation instead of assertion object
        instances, hence the need to use class names instead of class objects
        for `data` keys.
    """

    def get_record_key(self, obj):
        return obj.__name__

    def get_lookup_key(self, obj):
        return obj['type']

    def get_category(self, obj):
        return obj['meta_type']


registry = SerializedEntryRegistry()


@registry.bind_default()
class SerializedEntryRenderer(BaseRowRenderer):
    """Default fallback for all serialized entries."""

    def get_header(self, source, depth, row_idx):
        """Display the description or type as the header."""
        styles = [RowStyle(font=(constants.FONT, constants.FONT_SIZE_SMALL),
                           left_padding=constants.INDENT * depth)]

        header = source['description'] or source['type']
        return RowData(content=[header, '', '', '' ],
                       style=styles,
                       start=row_idx)

    def get_row_content(self, source):
        """
            All entries will either have a description or type,
            we display whatever is available.
        """
        return [source['description'] or source['type'], '', '', '']

    def get_row_data(self, source, depth, row_idx):
        """
          Most entries will be rendered as single rows, so we use
          `get_row_content` and `get_row_style` for simplicity.
        """
        result = RowData(
            content=self.get_row_content(source),
            style=self.get_row_style(source, depth),
            start=row_idx
        )
        return result

    def get_row_style(self, source, depth, **kwargs):
        """Default styling for all serialized entries, with small font size."""
        return RowStyle(
            font=(constants.FONT, constants.FONT_SIZE_SMALL),
            left_padding=constants.INDENT * depth,
            **kwargs
        )

    def get_style(self, source):
        if 'passed' in source and source['passed'] is False:
            return self.style.failing
        return self.style.passing

    def should_display(self, source):
        return self.get_style(source).display_assertion


@registry.bind(base.MatPlot)
class MatPlotRenderer(SerializedEntryRenderer):
    """Render a Matplotlib assertion from a serialized entry."""

    def get_row_data(self, source, depth, row_idx):
        """
        Load the Matplotlib graph from the saved image, set its height and width
        and add it to the row.
        """
        header = self.get_header(source, depth, row_idx)
        styles = [RowStyle(font=(constants.FONT, constants.FONT_SIZE_SMALL),
                           left_padding=constants.INDENT * (depth + 1),
                           text_color=colors.black)]

        img = Image(source['image_file_path'])
        img.drawWidth = source['width'] * inch
        img.drawHeight = source['height'] * inch

        return header + RowData(content=[img, '', '', ''],
                                start=header.end,
                                style=styles)


@registry.bind(base.TableLog)
class TableLogRenderer(SerializedEntryRenderer):
    """Render a Table from a serialized entry."""

    def get_row_data(self, source, depth, row_idx):
        """
        Reformat the rows from the serialized data into a format ReportLab
        accepts. Create a header and a ReportLab table and add it to the row.
        """
        header = self.get_header(source, depth, row_idx)
        row_style = [RowStyle(left_padding=constants.INDENT * (depth + 1))]
        table_style = format_table_style(constants.DISPLAYED_TABLE_STYLE)

        max_width = constants.PAGE_WIDTH - (depth * constants.INDENT)
        table = create_table(table=source['table'],
                             columns=source['columns'],
                             row_indices=source['indices'],
                             display_index=source['display_index'],
                             max_width=max_width,
                             style=table_style)

        return header + RowData(content=table,
                                start=header.end,
                                style=row_style)
