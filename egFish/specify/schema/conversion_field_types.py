from . import base, fields
from .generics import generic, method, next_method

class Column(base.Field):
    def __init__(self, path, *, process=None):
        super().__init__()
        if isinstance(path, str):
            self.path = [ path ]
        else:
            self.path = path

        self.process = process if process is not None else lambda v: v

    def check_against_table(self):
        from .conversion import get_primary_key_col

        table = self.record.source_table
        path = list(self.path)
        self.joins = {}
        while True:
            column_name = path.pop(0)
            assert column_name in table.c, 'Table "%s" has no column named "%s".' % (table, column_name)
            column = table.c[column_name]
            if len(path) > 0:
                table = list(column.foreign_keys)[0].column.table
                self.joins[table] = column == get_primary_key_col(table)
            else:
                break

        self.column_name = column_name
        self.column = table.c[self.column_name]

    def set_output_field(self):
        self.output_field = self.record.output_record.fields[self.__name__]
        try:
            self.check_field_types()
        except AssertionError as e:
            raise TypeError('Conversion field "%s" and schema field "%s" '
                            'have incompatible types.' % (self, self.output_field)) from e

    def check_field_types(self):
        check_field_types(self.output_field, self)

    def get_input_columns(self):
        return [ self.column ]

    def process_row(self, row):
        output_column = self.output_field.name
        return output_column, self.process(row[self.column])

class Enum(Column):
    def __init__(self, path, values, *args, **kwargs):
        super().__init__(path, *args, **kwargs)
        self.values = values

    def process_row(self, row):
        output_col, value = super().process_row(row)
        return output_col, self.values[value]

    def check_field_types(self):
        super().check_field_types()
        assert isinstance(self.output_field, fields.Text)

class ForeignKey(Column):
    def process_row(self, row):
        output_col, value = super().process_row(row)
        return output_col, str(value) if value is not None else None

    def check_field_types(self):
        super().check_field_types()
        assert isinstance(self.output_field, fields.Link)

@generic
def check_field_types(output_field, input_field):
    pass

@method(check_field_types)
def check_base_field_types(out: base.Field, field):
    assert isinstance(field, Column)

@method(check_field_types)
def check_link_field_types(out: fields.Link, field):
    assert isinstance(field, ForeignKey)