The **solution-downloader** is a helper tool that operates on top of ReCodEx CLI application and simplifies downloading batches of solution files from ReCodEx. This may be particularly useful for external evaluation tools, for instance:

- A post-evaluation that requires to be executed in a special environment (incompatible with ReCodEx backend).
- Collective processing where multiple solutions need to be evaluated together (tournaments).
- Similarity comparisons for detecting plagiarism.

## Installation

Make sure that Python 3.8+ and [recodex-cli](https://github.com/ReCodEx/cli) are installed (and `recodex` command is available in the `PATH`). Check out `requirements.txt`. You can install `recodex-cli` by yourself as
```
pip3 install recodex-cli --user
```

## How to use

### Preparing for the semester

1. Create a config file (e.g., `./config.yaml` which is the default name). Using `config.yaml.sample` as a template is recommended.

2. Update the config file, especially the group and exercise IDs (which you can read from ReCodEx web app URLs). The config specification details are below.

### Invocation

```
$> ./download.py [options] <exercise>
```

The *exercise* is a reference to a local exercise identifier (specified in the config file).

**Options:**
- `--config <path>` -- sets the path to the config YAML file, `./config.yaml` is used as default (the config file **must** exist)
- `--dest-dir <path>` -- sets the path to the directory where the solutions will be downloaded (if not present, nothing is downloaded), the directory is created if needed
- `--manifest <path>` -- sets the path to the output manifest CSV file (if not present, no manifest is generated)
- `--manifest-per-file` -- a flag that indicates the manifest file should hold one record for each solution file (instead of one per solution)

Either `--dest-dir` or `--manifest` options must be used (possibly both); otherwise, no action is taken. The `--manifest-per-file` can be used only when `--dest-dir` is used (the files are actually being loaded).

**Typical usage:** (assuming `./config.yaml` exists and holds all necessary data and exercise named `first`)
```
$> ./download.py --dest-dir ./first-solutions --manifest ./first-solutions.csv first
```


## Config specification

The config is a data structure encoded in a `yaml` file. It has the following top-level keys:

- `exercises` -- a collection translating local identifiers into ReCodEx exercise IDs. The local identifiers are used in the `exercise` CLI argument, which is more convenient than using GUID identifiers (which are rather long).
- `groups` -- a list of groups that should be searched for solutions to given exercises
- `solutions` -- a filter specification for solutions (only solutions that pass this filter are downloaded)
- `path` -- a list of (sub)directories defined by attribute descriptors how a path for downloaded solutions is constructed
- `manifest` -- specification of columns that are written into the manifest CSV file
- `translated_attributes` -- specification of additional attributes which are translated from ReCodEx attributes using translation tables stored in CSV files (e.g., translation of user IDs into user logins on a local system where the solutions will be re-evaluated)


### Groups

The list of groups holds objects with group identification:
- `id` -- mandatory, ReCodEx group GUID
- `recursive` -- optional bool flag, whether all sub-groups should be scanned as well (default is `false`)
- `archived` -- optional bool flag indicating, whether archived groups should be scanned as well (default is `false`)

### Solutions filter

The filter has the following options. If the bool flag is present, the solution needs to match its value (in the given attribute). If a bool flag is missing, the corresponding property is not checked in the filter.

- `accepted` -- a flag indicating whether the solution has been marked as accepted by the teacher
- `best` -- a flag indicating whether this is the best solution submitted by a user for a particular assignment (the best solution is either the accepted solution or the latest solution with the highest amount of points granted if no solution was accepted)
- `reviewed` -- a flag indicating whether a closed review exists for a solution
- `correctness` -- an integer with a correctness threshold in percent (only solutions with correctness greater or equal are downloaded)
- `createdAt` -- unix timestamp, only solutions created at the given time or later are downloaded
- `maxAge` -- similar filter like `createdAt`, but specifies relative time in seconds

### Download path

A list of metadata attribute references that are used to construct a path for each solution. The path should be constructed using such attributes that will create a unique location for each solution. For example:
```yaml
path:
  - 'admin.normLastName'
  - 'author.normName'
  - 'solution.createdAt'
```
will create a sub-path (within the base download directory) like:
```
Smith/John Doe/1672936007/
```
In which the submission from `January 05th, 2023, 16:26:47 (GMT)` of the student *John Doe* in the group of teacher *Smith* will be stored.

### Manifest

An ordered dictionary describing how the output manifest CSV file will be formatted. Each item of the dictionary corresponds to one column, the key holds the column name and the values are references to the metadata of the solutions.

### Referencing solution metadata

In some configurations (e.g., path or manifest), a user can reference data attributes related to the solution. An attribute reference is a string of keys separated by dots that navigate the _metadata_ structure* created for each processed solution. The metadata holds the following top-level keys:

- `group` -- [entity representing the group](https://github.com/ReCodEx/api/blob/master/app/model/view/GroupViewFactory.php) in which the exercise assignment was placed (and where the solution is submitted)
- `assignment` -- [entity representing the assignment](https://github.com/ReCodEx/api/blob/master/app/model/view/AssignmentViewFactory.php) (i.e., an instance of an exercise)
- `solution` -- the actual [metadata of the solution](https://github.com/ReCodEx/api/blob/master/app/model/view/AssignmentSolutionViewFactory.php) (e.g., evaluation results)
- `author` -- [entity of the user](https://github.com/ReCodEx/api/blob/master/app/model/view/UserViewFactory.php) who submitted the solution
- `admin` -- [entity of the first primary admin](https://github.com/ReCodEx/api/blob/master/app/model/view/UserViewFactory.php) of the group
- `path` -- string representing the relative download path where the solution files are stored

If the `--manifest-per-file` option is set, the manifest specification can also use
- `file` -- [entity of the solution file]()
- `zipEntry` -- a corresponding entity from `zipEntries` if the file is a whole-solution ZIP file
- `fileName` -- file name, possibly concatenated with the zip entry (if the file is a whole-solution ZIP file)

In addition, each [user entity](https://github.com/ReCodEx/api/blob/master/app/model/view/UserViewFactory.php) is augmented to contain the following:
- `fullName` -- concatenated given and last name
- `normFirstName` -- normalized given name (special characters are mapped to the nearest ASCII characters, so normalized name can be used in a path for instance)
- `normLastName` -- normalized last name
- `normName` -- normalized last name and given name

