# dotplug

dotplug(tmpname) is an application builder, used to quickly setup a working
environment using commands such as `cook add <env>`.

Dotplug works by first making sure the application exists on disk, this can also
be a buildable library. If it does it will just append to the current
environment, it's also possible to divide this step with a `make` step.

# Usage

The command `cook add json` will perform some checks:

First step is a sanity check, we need to know if the package already exists
in the database, there should be a flag to check forcefully update db to disk
information. This will most likely be solved by adding a file inside of the
package giving the status and other useful information.

Initial Make Step

  * Check current indexed list (database) for json entry
  * If it exists compare versions, if a version exists with a successfull
      make just report and exit.
  * If it doesn't exist we kick in the make step, the step will read the recipse
      for the json app and build it accordingly. On finalize if successful leave
      a valid exit code and pass it on.

*Debatable if ever implemented*, the implementatino wouldn't be that difficult
as the command could just eval a string. 

* the problem is that we are effectively launching a subshell when calling the 
    dot function. We would have to add a "postcmd" step that would read from an 
    input file. This is fragile and I really don't want to work around it. 
* Another option would be to pass the commands as pipes to the parent
    process(shell), this would ensure we're modifying the correct shell when
    executing. 
Add Step:

  * Modify the current environment in place
  * Make sure that json exists as a recipe
  * If we have 

eg. `cook make json` will look into your local storages for parts and check if
json is present. If it is it'll check on disk if the current version already
exists. If it does it'll just report and exit. If not, it'll continue with the
build process specified in the recipe.

It's also possible to make a recipe. A recipe is a special file just including
ingredients.


```
cook make json
# Add json to the current environment
cook add json
# Create a new system environment with just json appeneded
cook set json
```

# Premise

This script was a way to learn a little of everything, the main point was to get
was to learn async and python 3 syntax.
