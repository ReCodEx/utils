import csv


class AttributeTranslator:
    '''
    A translation table loaded from a CSV file.
    '''

    def __init__(self, name, config, base_dir) -> None:
        self.name = name
        self.key = config['key']
        self.translations = None
        if 'csv' in config:
            self._load_csv(base_dir, config['csv'])
        else:
            raise RuntimeError("No data source specification provided for translated attribute '{}'.".format(name))

    def _load_csv(self, base_dir, config) -> None:
        '''
        Load translation CSV file and initialize translation between existing key and newly added attribute.
        '''
        file = base_dir + '/' + config['file']
        delimiter = config.get('delimiter', ',')
        quotechar = config.get('quotechar', '"')
        header = config.get('header', False)
        key_column = config.get('key_column', 0)
        value_column = config.get('value_column', 1)
        if not header and (type(key_column) is not int or type(value_column) is not int):
            raise RuntimeError(
                "Both key and value columns must be referenced by integers when no CSV header is expected")

        self.translations = {}
        with open(file, 'r', encoding='utf-8') as fp:
            reader = csv.reader(fp, delimiter=delimiter, quotechar=quotechar)
            if header:
                column_names = next(reader)
                if type(key_column) is not int:
                    key_column = column_names.index(key_column)
                if type(value_column) is not int:
                    value_column = column_names.index(value_column)

            for row in reader:
                self.translations[row[key_column]] = row[value_column]

    def get_name(self):
        return self.name

    def get_key(self):
        return self.key

    def translate(self, key):
        return self.translations.get(str(key), None)
