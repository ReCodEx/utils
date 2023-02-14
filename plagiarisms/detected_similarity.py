import csv
import logging
import recodex_api


class DetectedSimilarity:
    '''
    Represents one similarity node (suspected plagiarisms for one tested solution of one other author).
    These data are uploaded together in a single add_similarities API call.
    '''

    def __init__(self, solution_id, file_id, author_id, similarity):
        self.solution_id = solution_id
        self.file_id = file_id
        self.author_id = author_id
        self.similarity = similarity
        self.files = {}

    def add_file(self, solution_id, file_id, o1, l1, o2, l2):
        self.files[solution_id] = self.files.get(solution_id, {})
        self.files[solution_id][file_id] = self.files[solution_id].get(file_id, [])
        self.files[solution_id][file_id].append([{'o': o1, 'l': l1}, {'o': o2, 'l': l2}])

    def upload(self, batch_id):
        # assemble the upload record from internal values
        files = []
        for solution_id in self.files:
            for file_id in self.files[solution_id]:
                files.append({
                    'solutionId': solution_id,
                    'solutionFileId': file_id,
                    'fragments': self.files[solution_id][file_id]
                })

        return recodex_api.add_similarity(batch_id, self.solution_id, {
            'solutionFileId': self.file_id,
            'authorId': self.author_id,
            'similarity': self.similarity,
            'files': files,
        })


def load_similarities_from_csv(file_name, columns, **kwargs):
    '''
    Load given CSV file with comparatrix output into a list of DetectedSimilarity objects.
    The columns is a dict structure (loaded from config) with important column names.
    Remaining named arguments are passed down to DictReader (e.g., useful for setting a delimiter).
    '''
    data = {}
    result = []
    count = 0
    with open(file_name, 'r', encoding="utf8") as f:
        reader = csv.DictReader(f, **kwargs)
        for row in reader:
            count += 1
            file_id = row[columns['file_id1']]  # first (tested) file
            author_id = row[columns['author_id']]  # author of the second (similar) file
            data[file_id] = data.get(file_id, {})
            if author_id not in data[file_id]:
                ds = DetectedSimilarity(row[columns['solution_id1']], file_id, author_id,
                                        float(row[columns['similarity']]) / 100.0)
                data[file_id][author_id] = ds
                result.append(ds)

            data[file_id][author_id].add_file(
                row[columns['solution_id2']],
                row[columns['file_id2']],
                int(row[columns['offset1']]),
                int(row[columns['length1']]),
                int(row[columns['offset2']]),
                int(row[columns['length2']])
            )

    logging.getLogger().debug("Comparator yielded {} matches, aggregated in {} similarity records".format(count, len(result)))
    return result


def save_similarities(tool_name, tool_params, similarities):
    '''
    Save loaded similarities in one batch upload (return the batch ID).
    Similarities arg holds a list of DetectedSimilarity objects loaded from CSV.
    '''
    batch_id = recodex_api.create_batch(tool_name, tool_params)
    for similarity in similarities:
        similarity.upload(batch_id)
    recodex_api.close_batch(batch_id)
    return batch_id
