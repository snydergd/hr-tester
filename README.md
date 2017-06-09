# Hackerrank Testing Tool #
Created to end the need for manually copying and pasting code and test cases to and from hackerrank.com.

## Features ##
- JSON configuration files used globally and per problem
- Allows for different language "modes", which can each be configured with a compiler, an interpreter, time limits, etc.
- Optionally, a PhantomJS script can be used to scrape a Hackerrank URL for default code template and test cases
- Git-like command syntax with subcommands, for quick operations

## Requirements ##
Note that some of the requirements are just what I used, but may be easy to do without.
- Unix-like system (mainly for execution-timing functionality; this might change)
- PhantomJS (optional; used to scrape website)
- Python 3 (though you might be able to get it to work with Python 2)
- Python modules: json, argcomplete (command-line completion), pyperclip (copy and paste)
- Bash (if you don't have this, just run `hackerrank.py` directly)

## Installation ##
### For bash ###
If you use bash, make sure `hr_completion` is included in your bashrc file.  Here is one way of doing it:
```
$ if [ ! -d ~/.bashrc.d/ ]; then mkdir ~/.bashrc.d/; echo "for FILE in ~/.bashrc.d/*; do . $FILE; done;" >> ~/.bashrc; fi; ln -s $PWD/hr_completion ~/.bashrc.d/; else mkdir ~/.bashrc.d/;
$ . hr_completion # if bash is still open, you might need to run this to make the command accessible
```

To uninstall, just remove the `hr_completion` code from your bashrc.  If you used the code above to create it, just do this to uninstall:
```
$ unlink ~/.bashrc.d/hr_completion
```

### For others ###
The simplest way is to just add hackerrank.py to your path.

## Configuration ##
**~/.hackerrank/settings.json**: Global settings for this tool<br>
**.hackerrank.json**: In any challenge directory; local settings file

## Usage ##
With Bash, you just need to know about the `hr` command, which will have tab completion.  If you're not using bash, then just use `hackerrank.py` instead or add it to your path.

Here are some of the main commands:
```
$ hr # changes directory to the hackerrank project directory from your config file
$ hr edit config # edit global configuration for this script
$ hr init morgan-and-substring # create a challenge directory named morgan-and-substring
$ hr init https://www.hackerrank.com/contests/world-codesprint-7/challenges/summing-pieces # use content from this page
$ hr test # run in challenge directory; test code against all input*.txt files and compare to corresponding output files
$ hr edit # run in challenge directory; open source code for this challenge in the editor from config file
$ hr edit localconfig # run in challenge directory; edit settings for this challenge
```
